"""
Integration tests for database models and persistence
"""

import asyncio

from sqlalchemy import delete, select

from backend.database.local_db import AsyncSessionLocal, init_db
from backend.database.models import (
    PromptResponseCache,
    ReductioAbsurdumProof,
    SupabaseSyncQueueItem,
)


class TestPromptResponseCache:
    """Pruebas de la cache de respuestas en DB"""

    def test_cache_db_model_exists(self):
        assert hasattr(PromptResponseCache, "engine")
        assert hasattr(PromptResponseCache, "model")
        assert hasattr(PromptResponseCache, "temperature")
        assert hasattr(PromptResponseCache, "max_tokens")
        assert hasattr(PromptResponseCache, "prompt_hash")

    def test_cache_persistence(self):
        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                cache_key = "test-cache-key-1"
                item = PromptResponseCache(
                    cache_key=cache_key,
                    engine="ollama",
                    model="llama3.2:latest",
                    node="LOCAL",
                    temperature=0.7,
                    max_tokens=500,
                    prompt_hash="abc123",
                    response_text="Test response",
                    tokens_in=100,
                    tokens_out=200,
                    latency_ms=500,
                    hit_count=0,
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key)
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.response_text == "Test response"
                assert persisted.hit_count == 0

                await db_session.execute(delete(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key))
                await db_session.commit()

        asyncio.run(scenario())

    def test_cache_hit_count_increment(self):
        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                cache_key = "test-cache-key-2"
                item = PromptResponseCache(
                    cache_key=cache_key,
                    engine="ollama",
                    model="llama3.2:latest",
                    node="LOCAL",
                    temperature=0.7,
                    max_tokens=500,
                    prompt_hash="def456",
                    response_text="Test response 2",
                    tokens_in=100,
                    tokens_out=200,
                    latency_ms=500,
                    hit_count=5,
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key)
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.hit_count == 5

                await db_session.execute(delete(PromptResponseCache).where(PromptResponseCache.cache_key == cache_key))
                await db_session.commit()

        asyncio.run(scenario())


class TestSupabaseSyncQueue:
    """Pruebas de la cola de sincronizacion con Supabase"""

    def test_sync_queue_model_fields(self):
        fields = [
            "id",
            "kind",
            "debate_id",
            "payload",
            "status",
            "retry_count",
            "next_attempt_at",
            "created_at",
        ]
        for field in fields:
            assert hasattr(SupabaseSyncQueueItem, field), f"Missing field: {field}"

    def test_sync_queue_persistence(self):
        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                item = SupabaseSyncQueueItem(
                    kind="debate",
                    debate_id="test-sync-1",
                    payload={"id": "test-sync-1", "topic": "test"},
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == "test-sync-1")
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.kind == "debate"
                assert persisted.status == "pending"

                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == "test-sync-1")
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_sync_queue_blocked_items(self):
        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                item = SupabaseSyncQueueItem(
                    kind="debate",
                    debate_id="test-blocked-1",
                    payload={"id": "test-blocked-1"},
                    status="blocked",
                    retry_count=3,
                )
                db_session.add(item)
                await db_session.commit()

                result = await db_session.execute(
                    select(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == "test-blocked-1")
                )
                persisted = result.scalar_one_or_none()
                assert persisted is not None
                assert persisted.status == "blocked"
                assert persisted.retry_count == 3

                await db_session.execute(
                    delete(SupabaseSyncQueueItem).where(SupabaseSyncQueueItem.debate_id == "test-blocked-1")
                )
                await db_session.commit()

        asyncio.run(scenario())


class TestReductioProofModel:
    """Pruebas del modelo de Reductio Absurdum"""

    def test_reductio_proof_model_fields(self):
        fields = [
            "debate_id",
            "iteration_number",
            "proposition",
            "extreme_case",
            "contradiction",
            "is_valid",
            "confidence_score",
            "questioning_agent",
            "challenged_agent",
            "consensus_areas",
            "weak_assumptions",
            "unquestioned_premises",
            "overall_complacency_risk",
            "recommendations",
        ]
        for field in fields:
            assert hasattr(ReductioAbsurdumProof, field), f"Missing field: {field}"
