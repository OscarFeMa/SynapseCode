"""
Synapse Council v2.0 - Local Engine Manager
Gestión de los 3 motores locales: Ollama, LM Studio, Jan
Implementa Protocolo Wake & Sleep para gestión de VRAM
"""

import asyncio
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

import structlog

from backend.adapters.jan import JanClient
from backend.adapters.lm_studio import LMStudioClient
from backend.adapters.ollama import OllamaClient
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class EngineType(Enum):
    """Tipos de motor local soportados"""

    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    JAN = "jan"


class LocalEngineManager:
    """
    Gestor de motores locales con:
    - Selección según disponibilidad y reputación
    - Protocolo Wake & Sleep (keep_alive: 0)
    - Degradación elegante a nube si PC B no responde
    """

    def __init__(self):
        self.engines: dict[EngineType, Any] = {
            EngineType.OLLAMA: OllamaClient(base_url=settings.worker_ollama_url),
            EngineType.LM_STUDIO: LMStudioClient(base_url=settings.worker_lm_studio_url),
            EngineType.JAN: JanClient(base_url=settings.worker_jan_url),
        }
        self.engine_health: dict[EngineType, bool] = {
            EngineType.OLLAMA: False,
            EngineType.LM_STUDIO: False,
            EngineType.JAN: False,
        }
        self.engine_failures: dict[EngineType, int] = {
            EngineType.OLLAMA: 0,
            EngineType.LM_STUDIO: 0,
            EngineType.JAN: 0,
        }
        self.circuit_broken_until: dict[EngineType, float] = {
            EngineType.OLLAMA: 0.0,
            EngineType.LM_STUDIO: 0.0,
            EngineType.JAN: 0.0,
        }
        self._health_cache_time: float | None = None
        self._health_cache_duration = 30.0  # segundos
        self._preload_tasks: dict[str, asyncio.Task] = {}

    async def health_check(self, engine_type: EngineType) -> dict[str, Any]:
        """Verifica salud de un motor específico"""
        # Circuit breaker check
        import time

        current_time = time.time()
        if self.circuit_broken_until[engine_type] > current_time:
            return {
                "status": "error",
                "error": f"Circuit breaker open for {int(self.circuit_broken_until[engine_type] - current_time)}s",
            }

        engine = self.engines.get(engine_type)
        if not engine:
            return {"status": "unknown", "error": "Engine not found"}

        try:
            result = await engine.health_check()
            is_online = result.get("status") == "online"
            self.engine_health[engine_type] = is_online

            if is_online:
                self.engine_failures[engine_type] = 0
            else:
                self._record_failure(engine_type)

            return result
        except Exception as e:
            logger.error("health_check_failed", engine=engine_type.value, error=str(e))

            # Auto-recuperación: intentar lanzar el servicio en el Worker (v2.2)
            try:
                from backend.engine.worker_launcher import worker_service_manager

                logger.info("local_engine.attempting_service_launch", engine=engine_type.value)
                result = await worker_service_manager.ensure_service_running(engine_type.value)
                if result.get("success"):
                    logger.info(
                        "local_engine.service_launched",
                        engine=engine_type.value,
                        action=result.get("action"),
                    )
                    # Re-verificar salud después de lanzar
                    try:
                        engine = self.engines.get(engine_type)
                        if engine:
                            result = await engine.health_check()
                            is_online = result.get("status") == "online"
                            self.engine_health[engine_type] = is_online
                            if is_online:
                                self.engine_failures[engine_type] = 0
                                return result
                    except Exception:
                        pass
            except ImportError:
                # WorkerServiceManager no disponible, fallback a RDP wake
                if settings.RDP_ENABLED:
                    try:
                        from backend.services.rdp_manager import RDPManager

                        logger.info(
                            "local_engine.attempting_auto_wake",
                            engine=engine_type.value,
                        )
                        await RDPManager.connect_to_worker_async(
                            hostname=settings.RDP_WORKER_HOSTNAME,
                            username=settings.RDP_WORKER_USERNAME,
                            password=settings.RDP_WORKER_PASSWORD,
                            rate_limit_id="health_auto_wake",
                        )
                    except Exception as wake_err:
                        logger.warning("local_engine.auto_wake_failed", error=str(wake_err))
            except Exception as launch_err:
                logger.warning("local_engine.service_launch_failed", error=str(launch_err))

            self.engine_health[engine_type] = False
            self._record_failure(engine_type)
            return {"status": "error", "error": str(e)}

    def _record_failure(self, engine_type: EngineType):
        """Registra fallo y abre el circuito si es necesario"""
        import time

        self.engine_failures[engine_type] += 1
        if self.engine_failures[engine_type] >= 3:
            logger.warning("circuit_breaker_opened", engine=engine_type.value, duration=60)
            self.circuit_broken_until[engine_type] = time.time() + 60.0
            self.engine_failures[engine_type] = 0  # Reset for next time

    async def check_all_health(self) -> dict[EngineType, dict[str, Any]]:
        """Verifica salud de todos los motores (con caché)"""
        current_time = asyncio.get_event_loop().time()

        # Usar caché si es reciente
        if self._health_cache_time and (current_time - self._health_cache_time) < self._health_cache_duration:
            return {
                engine: {"status": "online" if healthy else "offline"} for engine, healthy in self.engine_health.items()
            }

        # Verificar todos en paralelo
        results = await asyncio.gather(
            self.health_check(EngineType.OLLAMA),
            self.health_check(EngineType.LM_STUDIO),
            self.health_check(EngineType.JAN),
        )

        all_results = {
            EngineType.OLLAMA: results[0],
            EngineType.LM_STUDIO: results[1],
            EngineType.JAN: results[2],
        }

        self._health_cache_time = current_time
        return all_results

    async def get_available_engines(self) -> list[EngineType]:
        """Retorna lista de motores disponibles"""
        await self.check_all_health()
        return [engine for engine, healthy in self.engine_health.items() if healthy]

    async def generate(
        self,
        engine_type: EngineType,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Genera texto usando el motor especificado.
        Implementa Protocolo Wake & Sleep (keep_alive: 0 en Ollama).
        """
        logger.info("local_engine.generate.start", engine=engine_type.value, model=model)

        engine = self.engines.get(engine_type)
        if not engine:
            logger.error("local_engine.generate.unknown_engine", engine=engine_type.value)
            raise ValueError(f"Unknown engine: {engine_type}")

        # Verificar salud usando caché (evita HTTP en cada generación)
        logger.info(
            "local_engine.generate.checking_health",
            engine=engine_type.value,
            cached_health=self.engine_health.get(engine_type, False),
        )
        if not self.engine_health.get(engine_type, False):
            health = await self.health_check(engine_type)
            logger.info(
                "local_engine.generate.health_result",
                engine=engine_type.value,
                health_status=health.get("status"),
                health_error=health.get("error"),
            )
            if health.get("status") != "online":
                logger.error(
                    "local_engine.generate.engine_offline",
                    engine=engine_type.value,
                    error=health.get("error"),
                )
                raise RuntimeError(f"Engine {engine_type.value} is not available: {health.get('error')}")

        logger.info(
            "local_engine.generating",
            engine=engine_type.value,
            model=model,
            stream=stream,
        )

        try:
            if engine_type == EngineType.OLLAMA:
                # Ollama usa formato generate o chat
                options = {"temperature": temperature}
                if max_tokens:
                    options["num_predict"] = max_tokens

                logger.info(
                    "local_engine.generate.calling_ollama",
                    model=model,
                    prompt_preview=prompt[:50],
                )
                token_count = 0
                async for token in engine.generate(
                    model=model,
                    prompt=prompt,
                    system=system,
                    stream=stream,
                    options=options,
                ):
                    token_count += 1
                    yield token
                logger.info("local_engine.generate.ollama_completed", tokens_yielded=token_count)

            elif engine_type in [EngineType.LM_STUDIO, EngineType.JAN]:
                # LM Studio y Jan usan formato OpenAI chat
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                logger.info(
                    "local_engine.generate.calling_openai_compatible",
                    engine=engine_type.value,
                    model=model,
                )
                async for token in engine.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                ):
                    yield token

            logger.info("local_engine.completed", engine=engine_type.value, model=model)

        except Exception as e:
            logger.error(
                "local_engine.generate.failed",
                engine=engine_type.value,
                model=model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def chat(
        self,
        engine_type: EngineType,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Chat completion con historial de mensajes
        """
        engine = self.engines.get(engine_type)
        if not engine:
            raise ValueError(f"Unknown engine: {engine_type}")

        health = await self.health_check(engine_type)
        if health.get("status") != "online":
            raise RuntimeError(f"Engine {engine_type.value} is not available")

        try:
            if engine_type == EngineType.OLLAMA:
                async for token in engine.chat(model=model, messages=messages, stream=stream):
                    yield token
            else:
                async for token in engine.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                ):
                    yield token
        except Exception as e:
            logger.error("local_engine.chat_failed", engine=engine_type.value, error=str(e))
            raise

    def select_engine_for_slot(self, agent_slot: str) -> EngineType:
        """
        Selecciona motor óptimo según el slot del agente
        """
        slot_to_engine = {
            "analyst_local_a": EngineType.OLLAMA,
            "analyst_local_b": EngineType.LM_STUDIO,
            "critic_local_a": EngineType.OLLAMA,
            "critic_local_b": EngineType.JAN,
            "synth_local": EngineType.OLLAMA,
        }

        return slot_to_engine.get(agent_slot, EngineType.OLLAMA)

    async def generate_with_fallback(
        self,
        agent_slot: str,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Genera con motor primario, fallback a alternativas si falla
        """
        primary_engine = self.select_engine_for_slot(agent_slot)
        engines_to_try = [primary_engine] + [e for e in EngineType if e != primary_engine]

        last_error = None

        for engine_type in engines_to_try:
            try:
                async for token in self.generate(
                    engine_type=engine_type,
                    model=model,
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                ):
                    yield token
                return  # Éxito, salir

            except Exception as e:
                logger.warning(
                    "engine_fallback",
                    attempted=engine_type.value,
                    agent_slot=agent_slot,
                    error=str(e),
                )
                last_error = e
                continue

        # Si todos fallaron
        raise RuntimeError(f"All local engines failed. Last error: {last_error}")

    def schedule_ollama_preload(self, model: str | None) -> None:
        """Programa una precarga en segundo plano si no existe una ya activa para el modelo."""
        if not model:
            return

        existing = self._preload_tasks.get(model)
        if existing and not existing.done():
            return

        ollama_client = self.engines.get(EngineType.OLLAMA)
        if not ollama_client:
            return

        async def preload() -> None:
            try:
                await ollama_client.warm_model(model)
            except Exception as e:
                logger.debug("local_engine.preload_failed", model=model, error=str(e))
            finally:
                self._preload_tasks.pop(model, None)

        task = asyncio.create_task(preload())
        self._preload_tasks[model] = task
