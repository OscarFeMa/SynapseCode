"""
Synapse Council v2.0 - HTTP Client Manager

Gestiona clientes HTTPX compartidos con:
- Connection pooling centralizado
- Límites de conexiones configurables
- Timeout por servicio
- Cierre graceful de conexiones
- Métricas de uso

Elimina duplicación de clientes HTTP en adapters.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import structlog
from httpx import Limits

logger = structlog.get_logger()


@dataclass
class ClientConfig:
    """Configuración para un cliente HTTP"""

    timeout: float = 60.0
    max_keepalive: int = 10
    max_connections: int = 20
    retry_delay: float = 1.0
    headers: dict[str, str] | None = None


class HTTPClientManager:
    """
    Manager centralizado de clientes HTTPX.

    Singleton que gestiona conexiones HTTP eficientemente:
    - Evita crear múltiples clientes para el mismo servicio
    - Configura connection pooling apropiado
    - Proporciona timeouts específicos por servicio
    - Maneja cierre graceful de todas las conexiones

    Usage:
        # Obtener cliente para un servicio
        client = HTTPClientManager.get_client(
            "ollama",
            config=ClientConfig(timeout=120.0, max_connections=10)
        )

        # Usar el cliente
        response = await client.get("http://localhost:11434/api/tags")

        # Al finalizar aplicación, cerrar todo
        await HTTPClientManager.close_all()
    """

    _instance: Optional["HTTPClientManager"] = None
    _lock = asyncio.Lock()

    # Clientes por servicio
    _clients: dict[str, httpx.AsyncClient] = {}
    _configs: dict[str, ClientConfig] = {}
    _usage_count: dict[str, int] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_client(
        cls,
        service: str,
        config: ClientConfig | None = None,
        base_url: str | None = None,
    ) -> httpx.AsyncClient:
        """
        Obtiene cliente HTTP para un servicio.
        Crea uno nuevo si no existe o está cerrado.

        Args:
            service: Nombre del servicio (ollama, openrouter, supabase, etc)
            config: Configuración del cliente (usa default si None)
            base_url: URL base opcional para el cliente

        Returns:
            Cliente HTTPX configurado
        """
        # Verificar si existe y está abierto
        if service in cls._clients:
            client = cls._clients[service]
            if not client.is_closed:
                cls._usage_count[service] = cls._usage_count.get(service, 0) + 1
                return client
            # Cliente cerrado, eliminarlo
            del cls._clients[service]

        # Crear nuevo cliente
        config = config or cls._get_default_config(service)
        limits = Limits(
            max_keepalive_connections=config.max_keepalive,
            max_connections=config.max_connections,
        )

        client_kwargs = {
            "timeout": config.timeout,
            "limits": limits,
        }

        if base_url:
            client_kwargs["base_url"] = base_url

        if config.headers:
            client_kwargs["headers"] = config.headers

        client = httpx.AsyncClient(**client_kwargs)
        cls._clients[service] = client
        cls._configs[service] = config
        cls._usage_count[service] = 1

        logger.debug(
            "http_client.created",
            service=service,
            timeout=config.timeout,
            max_connections=config.max_connections,
        )

        return client

    @classmethod
    async def close(cls, service: str) -> None:
        """Cierra cliente específico"""
        if service in cls._clients:
            client = cls._clients[service]
            if not client.is_closed:
                await client.aclose()
                logger.debug("http_client.closed", service=service)
            del cls._clients[service]
            if service in cls._configs:
                del cls._configs[service]

    @classmethod
    async def close_all(cls) -> None:
        """Cierra todos los clientes HTTP"""
        services = list(cls._clients.keys())

        for service in services:
            try:
                await cls.close(service)
            except Exception as e:
                logger.warning("http_client.close_error", service=service, error=str(e))

        cls._clients.clear()
        cls._configs.clear()
        cls._usage_count.clear()

        logger.info("http_client.all_closed", count=len(services))

    @classmethod
    def get_metrics(cls) -> dict[str, Any]:
        """Obtiene métricas de uso de clientes"""
        return {
            service: {
                "usage_count": cls._usage_count.get(service, 0),
                "timeout": cls._configs.get(service, ClientConfig()).timeout,
                "is_closed": cls._clients.get(service, httpx.AsyncClient()).is_closed,
            }
            for service in cls._clients
        }

    @classmethod
    def _get_default_config(cls, service: str) -> ClientConfig:
        """Configuración por defecto según el servicio"""
        configs = {
            "ollama": ClientConfig(
                timeout=120.0,  # Ollama puede tardar en cargar modelos
                max_keepalive=5,
                max_connections=10,
            ),
            "openrouter": ClientConfig(timeout=60.0, max_keepalive=10, max_connections=20),
            "supabase": ClientConfig(timeout=30.0, max_keepalive=5, max_connections=10),
            "gemini": ClientConfig(timeout=60.0, max_keepalive=5, max_connections=10),
            "groq": ClientConfig(timeout=60.0, max_keepalive=5, max_connections=15),
            "deepseek": ClientConfig(timeout=60.0, max_keepalive=5, max_connections=10),
            "default": ClientConfig(timeout=60.0, max_keepalive=5, max_connections=10),
        }
        return configs.get(service, configs["default"])


# ============================================================================
# ADAPTERS REFACTORIZADOS
# ============================================================================


class ManagedHTTPClientMixin:
    """
    Mixin para adapters que usa HTTPClientManager.

    Reemplaza la creación manual de clientes HTTP.

    Usage:
        class MyAdapter(ManagedHTTPClientMixin):
            def __init__(self):
                self.service_name = "my_service"
                self._client = None

            async def some_method(self):
                client = self._get_client()
                response = await client.get(...)
    """

    service_name: str = "default"
    _client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP gestionado"""
        if self._client is None or self._client.is_closed:
            self._client = HTTPClientManager.get_client(self.service_name)
        return self._client

    async def close(self):
        """Cierra cliente (llamar a HTTPClientManager.close_all() al shutdown)"""
        # No cerramos aquí individualmente, se maneja globalmente
        pass


# ============================================================================
# HELPERS
# ============================================================================


async def make_request_with_retry(
    service: str, method: str, url: str, max_retries: int = 2, **kwargs
) -> httpx.Response:
    """
    Hace petición HTTP con retry automático.

    Args:
        service: Nombre del servicio para obtener cliente
        method: GET, POST, etc.
        url: URL completa
        max_retries: Número máximo de reintentos
        **kwargs: Argumentos adicionales para la petición

    Returns:
        Respuesta HTTPX

    Raises:
        httpx.HTTPError: Si agota reintentos
    """
    client = HTTPClientManager.get_client(service)
    config = HTTPClientManager._configs.get(service, ClientConfig())

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            # No reintentar errores 4xx (cliente)
            if e.response.status_code < 500:
                raise
            last_error = e

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < max_retries:
                delay = config.retry_delay * (attempt + 1)
                logger.warning(
                    "http.retry",
                    service=service,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)

    # Agotados reintentos
    raise last_error or httpx.HTTPError("Max retries exceeded")
