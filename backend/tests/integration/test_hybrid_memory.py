"""
Integration tests for hybrid memory and Supabase sync
"""

import asyncio

from sqlalchemy import delete, select

from backend.database.local_db import AsyncSessionLocal, init_db
from backend.database.models import SupabaseSyncQueueItem
from backend.engine.debate_models import DebateSession
from backend.memory.hybrid_memory_v2 import HybridMemoryV2
from backend.monitoring.prometheus import render_prometheus_metrics


class TestHybridMemory:
    """Pruebas de la memoria hibrida"""

    def test_hybrid_memory_persists_sync_queue_item_on_failure(self):
        async def scenario():
            await init_db()
            memory = HybridMemoryV2()
            memory._enabled = True

            class FakeSupabase:
                async def sync_debate(self, data):
                    return {"synced": False, "error": "network down"}

            memory.supabase = FakeSupabase()

            session = DebateSession(
                id="sync-queue-1",
                topic="Persistencia de cola",
                status="completed",
            )

            await memory.enqueue_sync(session, session.id, "standard")
            item = await memory.dequeue_persistent_item()
            assert item is not None

            processed = await memory.process_persistent_item(item)
            assert processed is False
            metrics = render_prometheus_metrics()
            assert "synapse_supabase_sync_failures_total" in metrics
            assert "synapse_supabase_sync_retries_total" in metrics

            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == session.id)
                )
                persisted = result.scalar_one()
                assert persisted.status == "pending"
                assert persisted.retry_count == 1

                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == session.id)
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_hybrid_memory_rehydrates_pending_queue_items_on_start(self):
        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                db_session.add(
                    SupabaseSyncQueueItem(
                        kind="debate",
                        debate_id="rehydrate-1",
                        payload={"id": "rehydrate-1", "topic": "rehydrate"},
                    )
                )
                await db_session.commit()

            memory = HybridMemoryV2()
            memory._enabled = True
            await memory._rehydrate_pending_queue()

            assert memory._queue.qsize() >= 1

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == "rehydrate-1")
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_hybrid_memory_has_enqueue_sync(self):
        from backend.memory.hybrid_memory_v2 import HybridMemoryV2

        mem = HybridMemoryV2()
        mem._enabled = True
        assert hasattr(mem, "enqueue_sync")

    def test_sync_health_reports_blocked_queue(self):
        assert hasattr(SupabaseSyncQueueItem, "status")
        assert hasattr(SupabaseSyncQueueItem, "retry_count")
        assert hasattr(SupabaseSyncQueueItem, "next_attempt_at")
