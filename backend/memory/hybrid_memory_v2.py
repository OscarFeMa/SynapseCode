"""
Hybrid Memory V2 - Sistema de memoria híbrida con cola async.
SQLite local (primario) + Supabase (background async).
Si Supabase falla, el sistema continúa sin interrupciones.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select

from backend.database.local_db import AsyncSessionLocal
from backend.database.models import SupabaseSyncQueueItem
from backend.monitoring.prometheus import (
    record_supabase_sync_failure,
    record_supabase_sync_retry,
    set_supabase_sync_queue_size,
)
from backend.services.supabase_sync import get_supabase_service

logger = structlog.get_logger()


class HybridMemoryV2:
    """
    Memoria híbrida con patrón "fire and forget" para Supabase.
    - SQLite: Siempre disponible, sincrónico, garantizado
    - Supabase: Async en background, no bloquea, opcional
    """

    def __init__(self):
        self.supabase = get_supabase_service()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._enabled: bool = self.supabase.enabled
        self._stats = {"queued": 0, "synced": 0, "failed": 0}

    async def start(self) -> None:
        """Inicia el worker de sincronización."""
        if self._enabled and self._task is None:
            await self._rehydrate_pending_queue()
            self._task = asyncio.create_task(self._worker())
            logger.info("hybrid_memory_v2.started")

    async def stop(self, timeout: float = 5.0) -> None:
        """Detiene el worker de forma graceful."""
        if self._task:
            try:
                # Esperar a que se procese la cola actual
                await asyncio.wait_for(self._queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("hybrid_memory_v2.stop_timeout", pending=self._queue.qsize())

            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

            logger.info("hybrid_memory_v2.stopped", stats=self._stats)

    async def enqueue_sync(self, session, session_id: str, mode: str) -> None:
        """
        Encola datos para sincronización con Supabase.
        Nunca lanza excepción al caller.
        """
        if not self._enabled:
            return  # Supabase no configurado, salir silenciosamente

        try:
            data = self._build_data(session, session_id, mode)
            async with AsyncSessionLocal() as db_session:
                db_session.add(
                    SupabaseSyncQueueItem(
                        kind="debate",
                        debate_id=session_id,
                        payload=data,
                    )
                )
                await db_session.commit()
            await self._queue.put(session_id)
            await self._update_queue_gauge()
            self._stats["queued"] += 1
        except Exception as e:
            # Silencioso - no crítico
            logger.debug("hybrid_memory_v2.enqueue_failed", error=str(e))

    async def _worker(self) -> None:
        """
        Worker que procesa la cola de sincronización.
        Si Supabase falla, solo loguea y continúa.
        """
        while True:
            try:
                # Esperar item con timeout para poder verificar cancellation
                _ = await asyncio.wait_for(self._queue.get(), timeout=30.0)

                try:
                    item = await self.dequeue_persistent_item()
                    if item:
                        processed = await self.process_persistent_item(item)
                        if processed:
                            self._stats["synced"] += 1
                            logger.debug(
                                "hybrid_memory_v2.synced",
                                session_id=item.payload.get("id"),
                            )
                        else:
                            self._stats["failed"] += 1
                except Exception as e:
                    # Silencioso - SQLite ya tiene los datos
                    logger.debug(
                        "hybrid_memory_v2.sync_failed",
                        session_id=getattr(item, "debate_id", None),
                        error=str(e),
                    )
                finally:
                    self._queue.task_done()
                    await self._update_queue_gauge()

            except asyncio.TimeoutError:
                # Normal, continuar loop
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("hybrid_memory_v2.worker_error", error=str(e))
                await asyncio.sleep(1)  # Evitar spam de errores

    def _build_data(self, session, session_id: str, mode: str) -> dict[str, Any]:
        """Construye payload para Supabase."""
        return {
            "id": session_id,
            "topic": getattr(session, "topic", ""),
            "mode": mode,
            "status": getattr(session, "status", ""),
            "final_verdict": getattr(session, "final_verdict", None),
            "total_tokens_out": sum(getattr(t, "tokens_out", 0) for t in getattr(session, "turns", [])),
            "total_latency_ms": sum(getattr(t, "latency_ms", 0) for t in getattr(session, "turns", [])),
            "turns": [
                {
                    "id": f"{session_id}_turn_{t.turn_number}",
                    "debate_id": session_id,
                    "turn_number": t.turn_number,
                    "agent_name": getattr(getattr(t, "agent", None), "name", "unknown"),
                    "model": getattr(getattr(t, "agent", None), "model", "unknown"),
                    "intervention_type": getattr(t, "intervention_type", "desconocido"),
                    "response_received": getattr(t, "response_received", "")[:15000],
                    "tokens_out": getattr(t, "tokens_out", 0),
                    "latency_ms": getattr(t, "latency_ms", 0),
                }
                for t in getattr(session, "turns", [])
            ],
        }

    def get_stats(self) -> dict[str, Any]:
        """Retorna estadísticas de sincronización."""
        return {
            "enabled": self._enabled,
            "queue_size": self._queue.qsize(),
            **self._stats,
        }

    async def get_persistent_queue_size(self) -> int:
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.status == "pending")
            )
            return len(result.scalars().all())

    async def dequeue_persistent_item(self) -> SupabaseSyncQueueItem | None:
        """Obtiene el próximo item elegible de la cola persistente."""
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(SupabaseSyncQueueItem)
                .where(SupabaseSyncQueueItem.status == "pending")
                .where(SupabaseSyncQueueItem.next_attempt_at <= datetime.now())
                .order_by(SupabaseSyncQueueItem.created_at.asc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def process_persistent_item(self, item: SupabaseSyncQueueItem) -> bool:
        """Procesa un item persistente; lo elimina solo si Supabase confirma éxito."""
        sync_result = {"synced": False, "error": "unsupported_kind"}
        if item.kind == "debate":
            sync_result = await self.supabase.sync_debate(item.payload)

        async with AsyncSessionLocal() as db_session:
            db_item = await db_session.get(SupabaseSyncQueueItem, item.id)
            if not db_item:
                return False

            if sync_result.get("synced"):
                await db_session.delete(db_item)
                await db_session.commit()
                return True

            reason = str(sync_result.get("error") or sync_result.get("reason") or "unknown")
            db_item.retry_count += 1
            db_item.last_error = reason
            db_item.next_attempt_at = datetime.now() + self._get_retry_delay(db_item.retry_count)
            db_item.status = "pending"
            await db_session.commit()
            record_supabase_sync_failure(reason)
            record_supabase_sync_retry(reason)
            return False

    def _get_retry_delay(self, retry_count: int) -> timedelta:
        """Backoff escalonado simple para reintentos de sync."""
        if retry_count <= 1:
            return timedelta(seconds=5)
        if retry_count == 2:
            return timedelta(seconds=30)
        if retry_count == 3:
            return timedelta(minutes=5)
        return timedelta(minutes=15)

    async def _rehydrate_pending_queue(self) -> None:
        """Vuelve a poner en cola en memoria los items pendientes persistidos."""
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(SupabaseSyncQueueItem)
                .where(SupabaseSyncQueueItem.status == "pending")
                .order_by(SupabaseSyncQueueItem.created_at.asc())
            )
            pending_items = result.scalars().all()

        for item in pending_items:
            await self._queue.put(item.debate_id)

        await self._update_queue_gauge()

    async def _update_queue_gauge(self) -> None:
        size = await self.get_persistent_queue_size()
        set_supabase_sync_queue_size(size)


# Instancia global
hybrid_memory_v2: HybridMemoryV2 | None = None


def get_hybrid_memory_v2() -> HybridMemoryV2:
    """Factory para instancia singleton."""
    global hybrid_memory_v2
    if hybrid_memory_v2 is None:
        hybrid_memory_v2 = HybridMemoryV2()
    return hybrid_memory_v2
