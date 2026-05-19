"""
Synapse Council v2.0 - Task Manager

Gestiona tareas asíncronas en background con:
- Captura de errores completa
- Logging contextual
- Límites de concurrencia
- Cancelación graceful
- Reintentos automáticos

Reemplaza el patrón 'fire-and-forget' problemático:
    asyncio.create_task(coro())  # ¡Errores se pierden!

Por:
    await task_manager.submit(coro(), context="reputation_update")
"""

import asyncio
import contextlib
import functools
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class TaskStatus(Enum):
    """Estados de una tarea en el manager"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class TaskInfo:
    """Información de una tarea registrada"""

    id: str
    context: str
    created_at: datetime
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 0


@dataclass
class TaskConfig:
    """Configuración para ejecución de tareas"""

    max_retries: int = 0
    retry_delay_seconds: float = 1.0
    timeout_seconds: float | None = None
    log_success: bool = True
    log_failure: bool = True
    propagate_errors: bool = False  # Si True, re-lanza excepciones


class BackgroundTaskManager:
    """
    Gestor de tareas asíncronas en background.

    Características:
    - Evita 'fire-and-forget' que oculta errores
    - Límites de concurrencia configurables
    - Cola de tareas pendientes
    - Reintentos automáticos con backoff
    - Logging estructurado de todas las operaciones
    - Cancelación graceful al shutdown

    Uso:
        task_manager = BackgroundTaskManager(max_concurrent=10)

        # Submit simple
        await task_manager.submit(
            reputation_service.update_after_turn(...),
            context="reputation_update"
        )

        # Submit con retries
        await task_manager.submit(
            supabase_sync.sync_debate(...),
            context="supabase_sync",
            config=TaskConfig(max_retries=3, retry_delay_seconds=2.0)
        )
    """

    _instance: Optional["BackgroundTaskManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern para acceso global"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        max_concurrent: int = 20,
        queue_size: int = 1000,
        default_config: TaskConfig | None = None,
    ):
        if self._initialized:
            return

        self._initialized = True
        self.max_concurrent = max_concurrent
        self.queue_size = queue_size
        self.default_config = default_config or TaskConfig()

        # Estado interno
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self._tasks: dict[str, asyncio.Task] = {}
        self._task_info: dict[str, TaskInfo] = {}
        self._task_counter = 0
        self._shutdown = False
        self._worker_task: asyncio.Task | None = None

        # Métricas
        self._metrics = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "retried": 0,
        }

    async def start(self) -> None:
        """Inicia el worker de procesamiento de cola"""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("task_manager.started", max_concurrent=self.max_concurrent)

    async def shutdown(self, timeout: float = 30.0) -> None:
        """
        Shutdown graceful del manager.

        Args:
            timeout: Segundos a esperar por tareas pendientes
        """
        self._shutdown = True
        logger.info("task_manager.shutting_down", pending=len(self._tasks))

        # Cancelar worker
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(self._worker_task, timeout=1.0)

        # Cancelar tareas pendientes
        pending_tasks = list(self._tasks.values())
        for task in pending_tasks:
            task.cancel()

        if pending_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    "task_manager.shutdown_timeout",
                    remaining=len(self._tasks),
                    timeout=timeout,
                )

        logger.info("task_manager.shutdown_complete", metrics=self._metrics)

    async def submit(
        self,
        coro: Callable[[], Any],
        context: str = "unnamed",
        config: TaskConfig | None = None,
        task_id: str | None = None,
    ) -> str:
        """
        Sube una tarea para ejecución en background.

        Args:
            coro: Corutina a ejecutar (lambda o functools.partial para args)
            context: Contexto descriptivo para logs
            config: Configuración específica de la tarea
            task_id: ID opcional (si no se genera uno)

        Returns:
            ID de la tarea para tracking

        Raises:
            RuntimeError: Si el manager está en shutdown
            asyncio.QueueFull: Si la cola está llena
        """
        if self._shutdown:
            raise RuntimeError("TaskManager is shutting down, cannot accept new tasks")

        # Asegurar que el worker está corriendo
        if self._worker_task is None or self._worker_task.done():
            await self.start()

        # Generar ID
        self._task_counter += 1
        task_id = task_id or f"{context}_{self._task_counter}_{datetime.now().strftime('%H%M%S')}"

        config = config or self.default_config

        # Crear info de tarea
        task_info = TaskInfo(
            id=task_id,
            context=context,
            created_at=datetime.now(),
            max_retries=config.max_retries,
        )
        self._task_info[task_id] = task_info

        # Encolar para procesamiento
        await self._queue.put((task_id, coro, config))
        self._metrics["submitted"] += 1

        logger.debug(
            "task_manager.submitted",
            task_id=task_id,
            context=context,
            queue_size=self._queue.qsize(),
        )

        return task_id

    async def submit_simple(self, coro: Callable[[], Any], context: str = "unnamed") -> str:
        """
        Versión simplificada de submit sin config personalizada.
        Usa la config por defecto del manager.
        """
        return await self.submit(coro, context, config=self.default_config)

    def get_task_status(self, task_id: str) -> TaskInfo | None:
        """Obtiene el estado de una tarea"""
        return self._task_info.get(task_id)

    def list_active_tasks(self, context_filter: str | None = None) -> list[TaskInfo]:
        """
        Lista tareas activas (pending o running).

        Args:
            context_filter: Si se proporciona, filtra por contexto
        """
        active = [
            info
            for info in self._task_info.values()
            if info.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]
        ]

        if context_filter:
            active = [t for t in active if t.context == context_filter]

        return active

    def get_metrics(self) -> dict[str, Any]:
        """Obtiene métricas del manager"""
        return {
            **self._metrics,
            "active": len(self.list_active_tasks()),
            "queue_size": self._queue.qsize(),
            "max_concurrent": self.max_concurrent,
        }

    # -------------------------------------------------------------------------
    # INTERNAL METHODS
    # -------------------------------------------------------------------------

    async def _worker_loop(self) -> None:
        """Loop principal del worker de procesamiento"""
        logger.info("task_manager.worker_started")

        while not self._shutdown:
            try:
                # Esperar tarea con timeout para poder verificar shutdown
                try:
                    task_id, coro, config = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except TimeoutError:
                    continue

                # Procesar con semáforo de concurrencia
                async with self._semaphore:
                    await self._execute_task(task_id, coro, config)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("task_manager.worker_error", error=str(e))

        logger.info("task_manager.worker_stopped")

    async def _execute_task(self, task_id: str, coro: Callable[[], Any], config: TaskConfig) -> None:
        """Ejecuta una tarea individual con manejo de errores y retries"""
        task_info = self._task_info.get(task_id)
        if task_info is None:
            logger.error("task_manager.task_not_found", task_id=task_id)
            return

        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now()

        attempt = 0
        last_error: Exception | None = None

        while attempt <= config.max_retries:
            attempt += 1

            try:
                # Ejecutar con timeout opcional
                if config.timeout_seconds:
                    await asyncio.wait_for(coro(), timeout=config.timeout_seconds)
                else:
                    await coro()

                # Éxito
                task_info.status = TaskStatus.COMPLETED
                task_info.completed_at = datetime.now()
                self._metrics["completed"] += 1

                if config.log_success:
                    logger.debug(
                        "task_manager.task_completed",
                        task_id=task_id,
                        context=task_info.context,
                        duration_ms=self._get_duration_ms(task_info),
                        attempts=attempt,
                    )

                return

            except TimeoutError:
                last_error = TimeoutError(f"Task timed out after {config.timeout_seconds}s")
                task_info.error = str(last_error)

                if attempt <= config.max_retries:
                    task_info.status = TaskStatus.RETRYING
                    task_info.retry_count += 1
                    self._metrics["retried"] += 1

                    logger.warning(
                        "task_manager.task_timeout_retry",
                        task_id=task_id,
                        context=task_info.context,
                        attempt=attempt,
                        max_retries=config.max_retries,
                        delay=config.retry_delay_seconds,
                    )

                    await asyncio.sleep(config.retry_delay_seconds)

            except Exception as e:
                last_error = e
                task_info.error = str(e)

                if attempt <= config.max_retries:
                    # Reintentar
                    task_info.status = TaskStatus.RETRYING
                    task_info.retry_count += 1
                    self._metrics["retried"] += 1

                    logger.warning(
                        "task_manager.task_error_retry",
                        task_id=task_id,
                        context=task_info.context,
                        attempt=attempt,
                        max_retries=config.max_retries,
                        error=str(e),
                        error_type=type(e).__name__,
                        delay=config.retry_delay_seconds,
                    )

                    await asyncio.sleep(config.retry_delay_seconds * attempt)  # Backoff exponencial

                else:
                    # Agotados reintentos
                    break

        # Fallo definitivo
        task_info.status = TaskStatus.FAILED
        task_info.completed_at = datetime.now()
        self._metrics["failed"] += 1

        if config.log_failure:
            logger.error(
                "task_manager.task_failed",
                task_id=task_id,
                context=task_info.context,
                attempts=attempt,
                error=str(last_error),
                error_type=type(last_error).__name__ if last_error else None,
            )

        # Propagar error si está configurado
        if config.propagate_errors and last_error:
            raise last_error

    def _get_duration_ms(self, task_info: TaskInfo) -> int | None:
        """Calcula duración de una tarea en ms"""
        if task_info.started_at and task_info.completed_at:
            delta = task_info.completed_at - task_info.started_at
            return int(delta.total_seconds() * 1000)
        return None


# ============================================================================
# DECORADOR PARA TAREAS
# ============================================================================


def background_task(
    context: str = "decorated_task",
    max_retries: int = 0,
    retry_delay: float = 1.0,
    timeout: float | None = None,
    log_success: bool = False,
):
    """
    Decorador para convertir una función en tarea background.

    Uso:
        @background_task(context="sync_data", max_retries=3)
        async def sync_to_supabase(data: dict) -> None:
            ...

        # Al llamar, se ejecuta en background
        await sync_to_supabase(data)  # Retorna inmediatamente con task_id
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> str:
            manager = BackgroundTaskManager()

            # Crear corutina parcialmente aplicada
            coro = functools.partial(func, *args, **kwargs)

            config = TaskConfig(
                max_retries=max_retries,
                retry_delay_seconds=retry_delay,
                timeout_seconds=timeout,
                log_success=log_success,
            )

            return await manager.submit(coro, context=context, config=config)

        return wrapper

    return decorator


# ============================================================================
# INSTANCIA GLOBAL
# ============================================================================

# Singleton accesible globalmente
task_manager = BackgroundTaskManager(max_concurrent=20)


# ============================================================================
# UTILIDADES
# ============================================================================


async def submit_reputation_update(
    reputation_service,
    model: str,
    provider: str,
    role: str,
    tokens_out: int,
    latency_ms: float,
    success: bool,
    intervention_type: str = "unknown",
) -> str:
    """
    Helper específico para updates de reputación.
    Usa config optimizada para este caso de uso.
    """
    return await task_manager.submit(
        lambda: reputation_service.update_after_turn(
            model=model,
            provider=provider,
            role=role,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            success=success,
            intervention_type=intervention_type,
        ),
        context="reputation_update",
        config=TaskConfig(
            max_retries=2,
            retry_delay_seconds=1.0,
            log_success=False,  # No loguear éxitos (muy frecuente)
            log_failure=True,
        ),
    )


async def submit_supabase_sync(sync_service, debate_data: dict) -> str:
    """Helper para sincronización con Supabase. No-op si no está habilitado."""
    # Verificar si el servicio está habilitado antes de intentar el sync
    if not sync_service.enabled:
        logger.debug("supabase_sync.disabled_skip", debate_id=debate_data.get("id"))
        return "skipped"

    return await task_manager.submit(
        lambda: sync_service.sync_debate(debate_data),
        context="supabase_sync",
        config=TaskConfig(
            max_retries=3,
            retry_delay_seconds=2.0,
            timeout_seconds=30.0,
            log_success=True,
            log_failure=True,
        ),
    )
