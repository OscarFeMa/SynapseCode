"""
SynapseCode Data Warehouse - Analytics & Historical Analysis
Gestiona agregaciones de datos para análisis histórico de debates
"""
import hashlib
import structlog
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    Session, SequentialDebate, SequentialDebateTurn,
    DebateAggregate, TopicTrending, ConsensusPattern,
    ModelPerformance, DailyMetricsSnapshot,
    ReductioAbsurdumProof, ModelReputation
)
from backend.database.local_db import AsyncSessionLocal
from backend.monitoring.prometheus import record_warehouse_debate_aggregated

logger = structlog.get_logger()


class WarehouseManager:
    """
    Gestor principal del Data Warehouse.
    Procesa debates completados y calcula agregaciones en tiempo real.
    """

    def __init__(self):
        self._hash_cache: Dict[str, str] = {}

    def _hash_topic(self, topic: str) -> str:
        """Genera hash SHA256 del topic para agrupación"""
        if topic in self._hash_cache:
            return self._hash_cache[topic]
        
        # Normalizar: lowercase, trim, remover espacios extra
        normalized = " ".join(topic.lower().strip().split())
        hash_val = hashlib.sha256(normalized.encode()).hexdigest()
        self._hash_cache[topic] = hash_val
        return hash_val

    def _get_date_str(self, dt: datetime) -> str:
        """Convierte datetime a string YYYY-MM-DD"""
        return dt.strftime("%Y-%m-%d")

    async def process_sequential_debate(self, debate_id: str) -> bool:
        """
        Procesa un SequentialDebate completado y actualiza el warehouse.
        Llamado cuando debate.status = "completed"
        """
        try:
            async with AsyncSessionLocal() as db:
                # Obtener debate con turns
                debate = await db.get(SequentialDebate, debate_id)
                if not debate or debate.status != "completed":
                    logger.warning("warehouse.sequential_debate_not_completed", debate_id=debate_id)
                    return False

                # Obtener turns
                result = await db.execute(
                    select(SequentialDebateTurn)
                    .where(SequentialDebateTurn.debate_id == debate_id)
                )
                turns = result.scalars().all()

                # Obtener reductio proofs si existen
                reductio_result = await db.execute(
                    select(ReductioAbsurdumProof)
                    .where(ReductioAbsurdumProof.debate_id == debate_id)
                )
                has_reductio = reductio_result.first() is not None

                # Calcular métricas
                unique_models = set(t.model for t in turns)
                started_at = debate.created_at
                duration_seconds = None
                if debate.completed_at and started_at:
                    duration_seconds = int((debate.completed_at - started_at).total_seconds())

                # Crear o actualizar DebateAggregate
                topic_hash = self._hash_topic(debate.topic)
                aggregate = await db.get(DebateAggregate, debate_id)
                
                if not aggregate:
                    aggregate = DebateAggregate(
                        id=debate_id,
                        debate_type="sequential",
                        topic_text=debate.topic,
                        topic_hash=topic_hash,
                        mode=debate.mode,
                        status=debate.status,
                        consensus_level=None,  # SequentialDebate no tiene consensus_level
                        rounds_executed=debate.total_turns,
                        total_tokens_in=debate.total_tokens_in,
                        total_tokens_out=debate.total_tokens_out,
                        total_latency_ms=debate.total_latency_ms,
                        estimated_cost_usd=0.0,  # SequentialDebate no tiene cost
                        started_at=started_at,
                        completed_at=debate.completed_at,
                        duration_seconds=duration_seconds,
                        has_tribunal_verdict=False,  # SequentialDebate no tiene tribunal
                        has_reductio_proofs=has_reductio,
                        unique_models_count=len(unique_models),
                    )
                    db.add(aggregate)
                else:
                    aggregate.status = debate.status
                    aggregate.rounds_executed = debate.total_turns
                    aggregate.total_tokens_in = debate.total_tokens_in
                    aggregate.total_tokens_out = debate.total_tokens_out
                    aggregate.total_latency_ms = debate.total_latency_ms
                    aggregate.completed_at = debate.completed_at
                    aggregate.duration_seconds = duration_seconds
                    aggregate.has_reductio_proofs = has_reductio
                    aggregate.unique_models_count = len(unique_models)
                    aggregate.updated_at = datetime.now(UTC)

                # Actualizar agregaciones derivadas
                await self._recalculate_topic_trending(db, aggregate)
                await self._update_consensus_patterns(db, aggregate)
                await self._recalculate_model_performance(db, turns)
                await self._recalculate_daily_metrics(db, aggregate)

                await db.commit()
                record_warehouse_debate_aggregated("sequential", debate.status)

                logger.info(
                    "warehouse.sequential_debate_processed",
                    debate_id=debate_id,
                    topic_hash=topic_hash,
                    turns_count=len(turns)
                )
                return True

        except Exception as e:
            logger.error("warehouse.sequential_debate_failed", debate_id=debate_id, error=str(e))
            return False

    async def process_session(self, session_id: str) -> bool:
        """
        Procesa una Session completada y actualiza el warehouse.
        Llamado cuando session.status = "COMPLETED"
        """
        try:
            async with AsyncSessionLocal() as db:
                # Obtener session con rounds y agent_calls
                session = await db.get(Session, session_id)
                if not session or session.status != "COMPLETED":
                    logger.warning("warehouse.session_not_completed", session_id=session_id)
                    return False

                # Obtener agent_calls para calcular unique models
                result = await db.execute(
                    select(func.distinct(Session.agent_calls.c.model_name))
                    .where(Session.agent_calls.c.session_id == session_id)
                )
                unique_models = result.scalars().all()

                # Calcular duration
                duration_seconds = None
                if session.completed_at and session.started_at:
                    duration_seconds = int((session.completed_at - session.started_at).total_seconds())

                # Crear o actualizar DebateAggregate
                topic_hash = self._hash_topic(session.query)
                aggregate = await db.get(DebateAggregate, session_id)
                
                if not aggregate:
                    aggregate = DebateAggregate(
                        id=session_id,
                        debate_type="session",
                        topic_text=session.query,
                        topic_hash=topic_hash,
                        mode="classic",
                        status=session.status,
                        consensus_level=session.consensus_level,
                        rounds_executed=session.rounds_executed,
                        total_tokens_in=session.total_tokens_in,
                        total_tokens_out=session.total_tokens_out,
                        total_latency_ms=0,  # Session no tiene latency total
                        estimated_cost_usd=session.estimated_cost_usd,
                        started_at=session.started_at,
                        completed_at=session.completed_at,
                        duration_seconds=duration_seconds,
                        has_tribunal_verdict=session.tribunal_verdict is not None,
                        has_reductio_proofs=False,  # Session no usa reductio
                        unique_models_count=len(unique_models),
                    )
                    db.add(aggregate)
                else:
                    aggregate.status = session.status
                    aggregate.consensus_level = session.consensus_level
                    aggregate.rounds_executed = session.rounds_executed
                    aggregate.total_tokens_in = session.total_tokens_in
                    aggregate.total_tokens_out = session.total_tokens_out
                    aggregate.estimated_cost_usd = session.estimated_cost_usd
                    aggregate.completed_at = session.completed_at
                    aggregate.duration_seconds = duration_seconds
                    aggregate.has_tribunal_verdict = session.tribunal_verdict is not None
                    aggregate.unique_models_count = len(unique_models)
                    aggregate.updated_at = datetime.now(UTC)

                # Actualizar agregaciones derivadas
                await self._recalculate_topic_trending(db, aggregate)
                await self._update_consensus_patterns(db, aggregate)
                await self._recalculate_daily_metrics(db, aggregate)

                await db.commit()
                record_warehouse_debate_aggregated("session", session.status)

                logger.info(
                    "warehouse.session_processed",
                    session_id=session_id,
                    topic_hash=topic_hash,
                    rounds=session.rounds_executed
                )
                return True

        except Exception as e:
            logger.error("warehouse.session_failed", session_id=session_id, error=str(e))
            return False

    async def _update_topic_trending(self, db: AsyncSession, aggregate: DebateAggregate):
        """Actualiza tabla topics_trending"""
        if not aggregate.completed_at:
            return

        date_str = self._get_date_str(aggregate.completed_at)
        
        # Buscar registro existente
        result = await db.execute(
            select(TopicTrending)
            .where(
                and_(
                    TopicTrending.date == date_str,
                    TopicTrending.topic_hash == aggregate.topic_hash
                )
            )
        )
        trending = result.scalar_one_or_none()

        if not trending:
            trending = TopicTrending(
                date=date_str,
                topic_hash=aggregate.topic_hash,
                topic_text=aggregate.topic_text,
                debate_count=1,
                total_turns=aggregate.rounds_executed,
                avg_consensus_level=self._consensus_to_float(aggregate.consensus_level),
                avg_duration_seconds=float(aggregate.duration_seconds) if aggregate.duration_seconds else None,
                unique_models_count=aggregate.unique_models_count,
            )
            db.add(trending)
        else:
            # Recalcular promedios
            total_debates = trending.debate_count + 1
            total_turns = trending.total_turns + aggregate.rounds_executed
            
            # Promedio ponderado
            new_avg_duration = None
            if trending.avg_duration_seconds and aggregate.duration_seconds:
                new_avg_duration = (
                    (trending.avg_duration_seconds * trending.debate_count + aggregate.duration_seconds) / total_debates
                )
            elif aggregate.duration_seconds:
                new_avg_duration = float(aggregate.duration_seconds)

            new_avg_consensus = self._consensus_to_float(aggregate.consensus_level)
            if trending.avg_consensus_level is not None:
                new_avg_consensus = (
                    (trending.avg_consensus_level * trending.debate_count + new_avg_consensus) / total_debates
                )

            trending.debate_count = total_debates
            trending.total_turns = total_turns
            trending.avg_consensus_level = new_avg_consensus
            trending.avg_duration_seconds = new_avg_duration
            trending.unique_models_count = max(trending.unique_models_count, aggregate.unique_models_count)
            trending.updated_at = datetime.now(UTC)

    async def _recalculate_topic_trending(self, db: AsyncSession, aggregate: DebateAggregate):
        """Recalcula un topic diario desde debates_aggregate para evitar doble conteo."""
        if not aggregate.completed_at:
            return

        date_str = self._get_date_str(aggregate.completed_at)
        result = await db.execute(
            select(DebateAggregate)
            .where(
                and_(
                    DebateAggregate.topic_hash == aggregate.topic_hash,
                    DebateAggregate.completed_at.is_not(None),
                )
            )
        )
        matching = [
            item for item in result.scalars().all()
            if self._get_date_str(item.completed_at) == date_str
        ]
        if not matching:
            return

        debate_count = len(matching)
        durations = [item.duration_seconds for item in matching if item.duration_seconds is not None]
        consensus_values = [
            self._consensus_to_float(item.consensus_level)
            for item in matching
            if self._consensus_to_float(item.consensus_level) is not None
        ]

        result = await db.execute(
            select(TopicTrending)
            .where(
                and_(
                    TopicTrending.date == date_str,
                    TopicTrending.topic_hash == aggregate.topic_hash,
                )
            )
        )
        trending = result.scalar_one_or_none()
        if not trending:
            trending = TopicTrending(
                date=date_str,
                topic_hash=aggregate.topic_hash,
                topic_text=aggregate.topic_text,
            )
            db.add(trending)

        trending.debate_count = debate_count
        trending.total_turns = sum(item.rounds_executed for item in matching)
        trending.avg_consensus_level = (
            sum(consensus_values) / len(consensus_values)
            if consensus_values
            else None
        )
        trending.avg_duration_seconds = (
            sum(durations) / len(durations)
            if durations
            else None
        )
        trending.unique_models_count = max(item.unique_models_count for item in matching)
        trending.updated_at = datetime.now(UTC)

    async def _update_consensus_patterns(self, db: AsyncSession, aggregate: DebateAggregate):
        """Actualiza tabla consensus_patterns"""
        if not aggregate.consensus_level:
            return

        # Buscar registro existente
        result = await db.execute(
            select(ConsensusPattern)
            .where(
                and_(
                    ConsensusPattern.topic_hash == aggregate.topic_hash,
                    ConsensusPattern.mode == aggregate.mode,
                    ConsensusPattern.consensus_level == aggregate.consensus_level
                )
            )
        )
        pattern = result.scalar_one_or_none()

        if not pattern:
            pattern = ConsensusPattern(
                topic_hash=aggregate.topic_hash,
                mode=aggregate.mode,
                consensus_level=aggregate.consensus_level,
                debate_count=1,
                avg_rounds_to_convergence=float(aggregate.rounds_executed),
                avg_tokens_per_debate=float(aggregate.total_tokens_out),
                success_rate=1.0 if aggregate.status == "completed" else 0.0,
            )
            db.add(pattern)
        else:
            total_debates = pattern.debate_count + 1
            pattern.debate_count = total_debates
            pattern.avg_rounds_to_convergence = (
                (pattern.avg_rounds_to_convergence * pattern.debate_count + aggregate.rounds_executed) / total_debates
            )
            pattern.avg_tokens_per_debate = (
                (pattern.avg_tokens_per_debate * pattern.debate_count + aggregate.total_tokens_out) / total_debates
            )
            success = 1.0 if aggregate.status == "completed" else 0.0
            pattern.success_rate = (
                (pattern.success_rate * pattern.debate_count + success) / total_debates
            )
            pattern.updated_at = datetime.now(UTC)

    async def _update_model_performance(self, db: AsyncSession, turns: List[SequentialDebateTurn]):
        """Actualiza tabla model_performance desde turns"""
        for turn in turns:
            # Buscar registro existente
            result = await db.execute(
                select(ModelPerformance)
                .where(
                    and_(
                        ModelPerformance.model_name == turn.model,
                        ModelPerformance.agent_role == turn.agent_role
                    )
                )
            )
            perf = result.scalar_one_or_none()

            if not perf:
                perf = ModelPerformance(
                    model_name=turn.model,
                    provider=turn.provider,
                    engine=turn.engine,
                    agent_role=turn.agent_role,
                    total_turns=1,
                    avg_tokens_out=float(turn.tokens_out),
                    avg_latency_ms=float(turn.latency_ms),
                    success_rate=1.0 if turn.status == "completed" else 0.0,
                )
                db.add(perf)
            else:
                total_turns = perf.total_turns + 1
                perf.total_turns = total_turns
                perf.avg_tokens_out = (
                    (perf.avg_tokens_out * perf.total_turns + turn.tokens_out) / total_turns
                )
                perf.avg_latency_ms = (
                    (perf.avg_latency_ms * perf.total_turns + turn.latency_ms) / total_turns
                )
                success = 1.0 if turn.status == "completed" else 0.0
                perf.success_rate = (
                    (perf.success_rate * perf.total_turns + success) / total_turns
                )
                perf.last_updated = datetime.now(UTC)

    async def _recalculate_model_performance(self, db: AsyncSession, turns: List[SequentialDebateTurn]):
        """Recalcula modelos afectados desde turns para que el reproceso sea idempotente."""
        affected_keys = {(turn.model, turn.agent_role) for turn in turns}

        for model_name, agent_role in affected_keys:
            result = await db.execute(
                select(SequentialDebateTurn)
                .where(
                    and_(
                        SequentialDebateTurn.model == model_name,
                        SequentialDebateTurn.agent_role == agent_role,
                    )
                )
            )
            model_turns = result.scalars().all()
            if not model_turns:
                continue

            result = await db.execute(
                select(ModelPerformance)
                .where(
                    and_(
                        ModelPerformance.model_name == model_name,
                        ModelPerformance.agent_role == agent_role,
                    )
                )
            )
            perf = result.scalar_one_or_none()
            first_turn = model_turns[0]
            if not perf:
                perf = ModelPerformance(
                    model_name=model_name,
                    provider=first_turn.provider,
                    engine=first_turn.engine,
                    agent_role=agent_role,
                )
                db.add(perf)

            total_turns = len(model_turns)
            perf.provider = first_turn.provider
            perf.engine = first_turn.engine
            perf.total_turns = total_turns
            perf.avg_tokens_out = sum(turn.tokens_out for turn in model_turns) / total_turns
            perf.avg_latency_ms = sum(turn.latency_ms for turn in model_turns) / total_turns
            perf.success_rate = (
                sum(1 for turn in model_turns if turn.status == "completed") / total_turns
            )
            perf.last_updated = datetime.now(UTC)

    async def _update_daily_metrics(self, db: AsyncSession, aggregate: DebateAggregate):
        """Actualiza tabla daily_metrics_snapshot"""
        if not aggregate.completed_at:
            return

        date_str = self._get_date_str(aggregate.completed_at)
        
        # Buscar registro existente
        result = await db.execute(
            select(DailyMetricsSnapshot)
            .where(DailyMetricsSnapshot.date == date_str)
        )
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            snapshot = DailyMetricsSnapshot(
                date=date_str,
                total_debates_completed=1 if aggregate.status == "completed" else 0,
                total_debates_failed=1 if aggregate.status == "failed" else 0,
                total_turns_executed=aggregate.rounds_executed,
                total_tokens_generated=aggregate.total_tokens_out,
                total_cost_usd=aggregate.estimated_cost_usd,
                avg_debate_duration_seconds=float(aggregate.duration_seconds) if aggregate.duration_seconds else None,
                unique_topics_count=1,
                active_models_count=aggregate.unique_models_count,
            )
            db.add(snapshot)
        else:
            snapshot.total_debates_completed += 1 if aggregate.status == "completed" else 0
            snapshot.total_debates_failed += 1 if aggregate.status == "failed" else 0
            snapshot.total_turns_executed += aggregate.rounds_executed
            snapshot.total_tokens_generated += aggregate.total_tokens_out
            snapshot.total_cost_usd += aggregate.estimated_cost_usd
            
            # Recalcular avg duration
            if snapshot.avg_debate_duration_seconds and aggregate.duration_seconds:
                total_completed = snapshot.total_debates_completed
                snapshot.avg_debate_duration_seconds = (
                    (snapshot.avg_debate_duration_seconds * (total_completed - 1) + aggregate.duration_seconds) / total_completed
                )
            elif aggregate.duration_seconds:
                snapshot.avg_debate_duration_seconds = float(aggregate.duration_seconds)

            # Actualizar unique topics (aproximado)
            snapshot.unique_topics_count = max(snapshot.unique_topics_count, 1)
            snapshot.active_models_count = max(snapshot.active_models_count, aggregate.unique_models_count)

    async def _recalculate_daily_metrics(self, db: AsyncSession, aggregate: DebateAggregate):
        """Recalcula el snapshot diario desde debates_aggregate para evitar doble conteo."""
        if not aggregate.completed_at:
            return

        date_str = self._get_date_str(aggregate.completed_at)
        result = await db.execute(
            select(DebateAggregate)
            .where(DebateAggregate.completed_at.is_not(None))
        )
        matching = [
            item for item in result.scalars().all()
            if self._get_date_str(item.completed_at) == date_str
        ]
        if not matching:
            return

        durations = [item.duration_seconds for item in matching if item.duration_seconds is not None]
        result = await db.execute(
            select(DailyMetricsSnapshot)
            .where(DailyMetricsSnapshot.date == date_str)
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            snapshot = DailyMetricsSnapshot(date=date_str)
            db.add(snapshot)

        snapshot.total_debates_completed = sum(1 for item in matching if item.status == "completed")
        snapshot.total_debates_failed = sum(1 for item in matching if item.status == "failed")
        snapshot.total_turns_executed = sum(item.rounds_executed for item in matching)
        snapshot.total_tokens_generated = sum(item.total_tokens_out for item in matching)
        snapshot.total_cost_usd = sum(item.estimated_cost_usd for item in matching)
        snapshot.avg_debate_duration_seconds = (
            sum(durations) / len(durations)
            if durations
            else None
        )
        snapshot.unique_topics_count = len({item.topic_hash for item in matching})
        snapshot.active_models_count = max(item.unique_models_count for item in matching)

    def _consensus_to_float(self, consensus_level: Optional[str]) -> Optional[float]:
        """Convierte consensus_level string a float 0-1"""
        if not consensus_level:
            return None
        mapping = {
            "CONSENSUS_REACHED": 1.0,
            "PARTIAL_CONSENSUS": 0.5,
            "DIVERGENT": 0.0,
        }
        return mapping.get(consensus_level, None)

    async def sync_to_supabase(self, table_name: str, data: Dict[str, Any]) -> bool:
        """
        Sincroniza datos a Supabase usando el queue existente.
        """
        try:
            from backend.services.supabase_sync import supabase_sync_queue
            
            await supabase_sync_queue.enqueue(
                kind=f"warehouse_{table_name}",
                debate_id=data.get("id", "unknown"),
                payload=data
            )
            
            logger.info("warehouse.sync_queued", table=table_name, id=data.get("id"))
            return True
            
        except Exception as e:
            logger.error("warehouse.sync_failed", table=table_name, error=str(e))
            return False

    async def backfill_historical_data(self) -> Dict[str, int]:
        """
        Procesa todos los debates históricos para poblar el warehouse.
        Útil para inicializar el warehouse con datos existentes.
        """
        stats = {
            "sequential_processed": 0,
            "session_processed": 0,
            "failed": 0,
        }

        try:
            async with AsyncSessionLocal() as db:
                # Procesar SequentialDebates completados
                result = await db.execute(
                    select(SequentialDebate)
                    .where(SequentialDebate.status == "completed")
                )
                debates = result.scalars().all()
                
                for debate in debates:
                    success = await self.process_sequential_debate(debate.id)
                    if success:
                        stats["sequential_processed"] += 1
                    else:
                        stats["failed"] += 1

                # Procesar Sessions completadas
                result = await db.execute(
                    select(Session)
                    .where(Session.status == "COMPLETED")
                )
                sessions = result.scalars().all()
                
                for session in sessions:
                    success = await self.process_session(session.id)
                    if success:
                        stats["session_processed"] += 1
                    else:
                        stats["failed"] += 1

            logger.info("warehouse.backfill_completed", stats=stats)
            return stats

        except Exception as e:
            logger.error("warehouse.backfill_failed", error=str(e))
            stats["failed"] = -1
            return stats


# Instancia global
warehouse_manager = WarehouseManager()
