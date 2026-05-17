"""
Synapse Council v2.0 - Ollama Adapter
Cliente async para Ollama API (usa formato nativo, no OpenAI-compatible)
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import structlog

from backend.adapters.http_client_manager import HTTPClientManager
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class OllamaClient:
    """Cliente async para Ollama (motor local)"""

    SERVICE_NAME = "ollama"

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS
        self.max_retries = settings.OLLAMA_MAX_RETRIES
        self.keep_alive = settings.OLLAMA_KEEP_ALIVE
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Cliente HTTPX persistente (Connection Pooling)"""
        # Usar HTTPClientManager para gestión centralizada
        return HTTPClientManager.get_client(self.SERVICE_NAME, base_url=self.base_url)

    async def close(self):
        """No cerramos individualmente - gestión centralizada en shutdown"""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Verifica conexión con Ollama y lista modelos disponibles"""
        try:
            client = self.client
            response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "unknown") for m in data.get("models", [])]
                return {
                    "status": "online",
                    "models_available": len(models),
                    "models": models[:10],  # Primeros 10
                    "url": self.base_url,
                }
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "url": self.base_url,
                }
        except httpx.ConnectError:
            return {
                "status": "offline",
                "error": "Cannot connect to Ollama. Is it running?",
                "url": self.base_url,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "url": self.base_url}

    async def ensure_model_loaded(self, model: str):
        """
        Asegura que el modelo esté cargado antes de usarlo.
        Para modelos de Ollama Cloud (sufijo :cloud), usa pull_model.
        """
        # Detectar modelos de Ollama Cloud
        if ":cloud" in model:
            logger.info("ollama.ensure.cloud_model", model=model)
            try:
                async for progress in self.pull_model(model):
                    # El pull_model ya yieldea el progreso, solo loggear
                    if "status" in progress:
                        logger.debug(
                            "ollama.pull.progress",
                            model=model,
                            status=progress.get("status"),
                        )
                logger.info("ollama.ensure.cloud_model_loaded", model=model)
            except Exception as e:
                logger.warning("ollama.ensure.pull_failed", model=model, error=str(e))
                # Continuar de todas formas, Ollama puede cargar on-demand

    async def warm_model(self, model: str, keep_alive: Optional[int] = None) -> bool:
        """
        Precarga un modelo en memoria sin generar contenido útil.
        Reintenta hasta 2 veces en caso de HTTP 500 (GPU loading race).
        """
        keep_alive_value = settings.OLLAMA_PRELOAD_KEEP_ALIVE if keep_alive is None else keep_alive
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    logger.info("ollama.warm_model.retry", model=model, attempt=attempt + 1)
                    await asyncio.sleep(2)
                logger.info("ollama.warm_model.start", model=model, keep_alive=keep_alive_value)
                client = self.client
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": "",
                        "stream": False,
                        "keep_alive": keep_alive_value,
                        "options": {"num_predict": 0},
                    },
                    timeout=30.0,
                )
                if response.status_code == 200:
                    logger.info("ollama.warm_model.success", model=model)
                    return True
                logger.warning(
                    "ollama.warm_model.failed",
                    model=model,
                    status_code=response.status_code,
                )
                if response.status_code == 500 and attempt < max_attempts - 1:
                    continue
                return False
            except Exception as e:
                logger.warning("ollama.warm_model.error", model=model, error=str(e))
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2)
                    continue
                return False
        return False

    async def unload_model(self, model: str) -> bool:
        """Descarga un modelo específico de la RAM del worker

        Esto libera memoria antes de cargar un nuevo modelo,
        evitando errores de falta de RAM en el worker.
        """
        try:
            logger.info("ollama.unload_model.start", model=model, base_url=self.base_url)
            client = self.client
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": "", "keep_alive": 0},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("done_reason") == "unload":
                    logger.info("ollama.unload_model.success", model=model)
                    return True
                else:
                    logger.warning(
                        "ollama.unload_model.unexpected_response",
                        model=model,
                        done_reason=data.get("done_reason"),
                    )
                    return False
            else:
                logger.warning(
                    "ollama.unload_model.failed",
                    model=model,
                    status_code=response.status_code,
                )
                return False

        except Exception as e:
            logger.error("ollama.unload_model.error", model=model, error=str(e))
            return False

    def _is_cuda_error(self, error_text: str) -> bool:
        """Detecta errores CUDA que requieren recuperación de GPU"""
        cuda_indicators = [
            "cuda error",
            "cuda out of memory",
            "shared object initialization failed",
            "llama runner process has terminated",
        ]
        return any(indicator in error_text.lower() for indicator in cuda_indicators)

    async def _recover_from_cuda_error(self) -> bool:
        """Intenta recuperarse de un error CUDA liberando memoria GPU"""
        try:
            logger.info("ollama.cuda_recovery.starting")
            # Intentar descargar todos los modelos conocidos
            try:
                tags_response = await self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if tags_response.status_code == 200:
                    models = tags_response.json().get("models", [])
                    for m in models[:5]:  # Limitar a 5 para no saturar
                        model_name = m.get("name", "")
                        if model_name:
                            try:
                                await self.client.post(
                                    f"{self.base_url}/api/generate",
                                    json={"model": model_name, "prompt": "", "keep_alive": 0},
                                    timeout=5.0,
                                )
                            except Exception:
                                pass
            except Exception:
                pass
            # Esperar a que la GPU se recupere
            await asyncio.sleep(3)
            logger.info("ollama.cuda_recovery.completed")
            return True
        except Exception as e:
            logger.warning("ollama.cuda_recovery.failed", error=str(e))
            return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Genera texto con Ollama
        Yields tokens si stream=True, o texto completo al final
        """
        logger.debug("ollama.generate.start", model=model, prompt_len=len(prompt))

        # Asegurar que el modelo esté cargado (especialmente para cloud models)
        await self.ensure_model_loaded(model)

        # Siempre usar stream=True para asegurar consumo completo
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": options or {},
            "keep_alive": self.keep_alive,
        }

        if system:
            payload["system"] = system

        client = self.client
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    logger.info("ollama.generate.retry", model=model, attempt=attempt + 1)
                    if await self._recover_from_cuda_error():
                        await asyncio.sleep(2)
                    else:
                        break
                logger.info(
                    "ollama.generate.sending_request",
                    model=model,
                    url=f"{self.base_url}/api/generate",
                )
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    logger.info("ollama.generate.response_started", status_code=response.status_code)
                    if response.status_code != 200:
                        error_body = await response.aread()
                        error_text = error_body.decode("utf-8", errors="replace")[:500]
                        logger.error(
                            "ollama.generate.http_error",
                            model=model,
                            status_code=response.status_code,
                            error=error_text,
                        )
                        if self._is_cuda_error(error_text) and attempt < max_attempts - 1:
                            continue
                        raise RuntimeError(f"Ollama generate returned HTTP {response.status_code}: {error_text}")
                    if stream:
                        token_count = 0
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    if "response" in data:
                                        token_count += 1
                                        yield data["response"]
                                    if data.get("done", False):
                                        logger.info(
                                            "ollama.generate.done",
                                            model=model,
                                            tokens_yielded=token_count,
                                        )
                                        break
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        "ollama.generate.json_decode_error",
                                        line=line[:100],
                                        error=str(e),
                                    )
                                    continue
                    else:
                        text = ""
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)
                                    if "response" in data:
                                        text += data["response"]
                                    if data.get("done", False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                        yield text
                    return  # Éxito, salir del retry loop
            except RuntimeError as e:
                if attempt < max_attempts - 1 and self._is_cuda_error(str(e)):
                    logger.warning("ollama.generate.cuda_error_retry", model=model, error=str(e))
                    continue
                raise
            except Exception as e:
                logger.error(
                    "ollama.generate.exception",
                    model=model,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise e

    async def chat(self, model: str, messages: list, stream: bool = True) -> AsyncGenerator[str, None]:
        """
        Chat completion con Ollama (formato chat)
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "keep_alive": self.keep_alive,
        }

        client = self.client
        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise e

    async def pull_model(self, model: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Descarga un modelo de Ollama Library o Cloud.
        Yields progreso de descarga.
        """
        logger.info("ollama.pull.start", model=model)
        payload = {"name": model, "stream": True}
        client = self.client

        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json=payload,
                timeout=None,  # Las descargas pueden ser lentas
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)
        except Exception as e:
            logger.error("ollama.pull.failed", model=model, error=str(e))
            raise e
