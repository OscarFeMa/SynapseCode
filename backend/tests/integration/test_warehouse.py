"""
Integration tests for data warehouse
"""

import asyncio
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from backend.database.local_db import AsyncSessionLocal, init_db
from backend.database.models import (
    ConsensusPattern,
    DailyMetricsSnapshot,
    DebateAggregate,
    ModelPerformance,
    SequentialDebate,
    SequentialDebateTurn,
    TopicTrending,
)
from backend.database.warehouse import WarehouseManager, warehouse_manager


class TestDataWarehouse:
    """Pruebas del sistema de Data Warehouse"""

    def test_warehouse_models_exist(self):
        assert hasattr(DebateAggregate, "id")
        assert hasattr(DebateAggregate, "topic_text")
        assert hasattr(TopicTrending, "topic_text")
        assert hasattr(ConsensusPattern, "consensus_level")
        assert hasattr(ConsensusPattern, "success_rate")
        assert hasattr(ModelPerformance, "model_name")
        assert hasattr(DailyMetricsSnapshot, "date")

    def test_warehouse_manager_imports(self):
        assert hasattr(WarehouseManager, "process_sequential_debate")
        assert hasattr(WarehouseManager, "backfill_historical_data")
        assert warehouse_manager is not None

    def test_warehouse_processes_sequential_debate_idempotently(self):
        debate_id = f"warehouse-{uuid.uuid4()}"
        topic = f"Warehouse topic {uuid.uuid4()}"
        model_name = f"warehouse-model-{uuid.uuid4()}"
        completed_at = datetime(2099, 1, 2, 12, 0, tzinfo=UTC)
        created_at = datetime(2099, 1, 2, 11, 59, tzinfo=UTC)

        async def scenario():
            await init_db()
            manager = WarehouseManager()
            topic_hash = manager._hash_topic(topic)

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(delete(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                await db_session.execute(delete(DebateAggregate).where(DebateAggregate.id == debate_id))
                await db_session.execute(delete(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-01-02"))
                await db_session.execute(delete(ModelPerformance).where(ModelPerformance.model_name == model_name))
                await db_session.execute(
                    delete(SequentialDebateTurn).where(SequentialDebateTurn.debate_id == debate_id)
                )
                await db_session.execute(delete(SequentialDebate).where(SequentialDebate.id == debate_id))
                db_session.add(
                    SequentialDebate(
                        id=debate_id,
                        topic=topic,
                        mode="standard",
                        status="completed",
                        total_turns=2,
                        total_tokens_in=30,
                        total_tokens_out=70,
                        total_latency_ms=1500,
                        created_at=created_at,
                        completed_at=completed_at,
                    )
                )
                db_session.add_all(
                    [
                        SequentialDebateTurn(
                            debate_id=debate_id,
                            turn_number=1,
                            agent_id="a1",
                            agent_name="Analyst",
                            agent_role="analyst",
                            model=model_name,
                            provider="local",
                            node="LOCAL",
                            engine="ollama",
                            prompt_sent="p1",
                            response_received="r1",
                            tokens_in=10,
                            tokens_out=20,
                            latency_ms=500,
                            status="completed",
                        ),
                        SequentialDebateTurn(
                            debate_id=debate_id,
                            turn_number=2,
                            agent_id="a2",
                            agent_name="Critic",
                            agent_role="critic",
                            model=model_name,
                            provider="local",
                            node="LOCAL",
                            engine="ollama",
                            prompt_sent="p2",
                            response_received="r2",
                            tokens_in=20,
                            tokens_out=50,
                            latency_ms=1000,
                            status="completed",
                        ),
                    ]
                )
                await db_session.commit()

            assert await manager.process_sequential_debate(debate_id) is True
            assert await manager.process_sequential_debate(debate_id) is True

            async with AsyncSessionLocal() as db_session:
                aggregate = await db_session.get(DebateAggregate, debate_id)
                topic_row = (
                    await db_session.execute(select(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                ).scalar_one()
                daily = (
                    await db_session.execute(
                        select(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-01-02")
                    )
                ).scalar_one()
                model_rows = (
                    (
                        await db_session.execute(
                            select(ModelPerformance).where(ModelPerformance.model_name == model_name)
                        )
                    )
                    .scalars()
                    .all()
                )

                assert aggregate.duration_seconds == 60
                assert aggregate.unique_models_count == 1
                assert topic_row.debate_count == 1
                assert topic_row.total_turns == 2
                assert daily.total_debates_completed == 1
                assert daily.total_tokens_generated == 70
                assert len(model_rows) == 2
                assert {row.agent_role for row in model_rows} == {"analyst", "critic"}

                await db_session.execute(delete(TopicTrending).where(TopicTrending.topic_hash == topic_hash))
                await db_session.execute(delete(DailyMetricsSnapshot).where(DailyMetricsSnapshot.date == "2099-01-02"))
                await db_session.execute(delete(ModelPerformance).where(ModelPerformance.model_name == model_name))
                await db_session.execute(delete(DebateAggregate).where(DebateAggregate.id == debate_id))
                await db_session.execute(
                    delete(SequentialDebateTurn).where(SequentialDebateTurn.debate_id == debate_id)
                )
                await db_session.execute(delete(SequentialDebate).where(SequentialDebate.id == debate_id))
                await db_session.commit()

        asyncio.run(scenario())

    def test_backfill_script_exists(self):
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "scripts",
            "backfill_warehouse.py",
        )
        assert os.path.exists(doc_path)

    def test_analytics_queries_doc_exists(self):
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "docs",
            "ANALYTICS_QUERIES.md",
        )
        assert os.path.exists(doc_path)
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "SELECT" in content or "sql" in content.lower()
