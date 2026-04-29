"""
Reputation Manager - Sistema de reputación EMA para modelos.
Calcula scores basados en desempeño histórico.
"""

from typing import Optional
from datetime import datetime
import structlog

from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import ModelReputation
from sqlalchemy import select, update

logger = structlog.get_logger()


class ReputationManager:
    """
    Gestiona reputación de modelos usando EMA (Exponential Moving Average).
    Scores: TSA, IID, PVT, Efficiency.
    """
    
    ALPHA = 0.3  # Factor EMA: 0.3 = últimos ~3 debates pesan 65%
    
    async def update_after_turn(
        self,
        model: str,
        provider: str,
        role: str,
        tokens_out: int,
        latency_ms: float,
        success: bool,
        intervention_type: str = 'desconocido'
    ) -> None:
        """
        Actualiza reputación después de un turno.
        Siempre captura excepciones - nunca propaga errores.
        """
        # Verificar si reputación está habilitada
        if not get_settings().AGENT_REPUTATION_ENABLED:
            return
        
        try:
            # Calcular métricas
            efficiency = min((tokens_out / max(latency_ms, 1)) * 1000 / 10.0, 1.0)
            
            # TSA: Tasa de Supervivencia de Argumentos
            # Baja si el agente fue refutado
            tsa_new = 1.0 if intervention_type not in ['refutacion', 'refutation'] else 0.3
            
            # IID: Índice de Independencia Dialéctica
            # Alta si el agente hizo argumentos, críticas o refutaciones
            iid_new = 1.0 if intervention_type in ['argumento', 'refutacion', 'critica'] else 0.5
            
            # PVT: Puntuación de Verificación Técnica
            # Basada en éxito del turno
            pvt_new = 1.0 if success else 0.0
            
            async with AsyncSessionLocal() as db:
                # Buscar reputación existente
                result = await db.execute(
                    select(ModelReputation)
                    .where(ModelReputation.model == model, ModelReputation.role == role)
                )
                rep = result.scalar_one_or_none()
                
                if rep is None:
                    # Crear nueva entrada
                    rep = ModelReputation(
                        model=model,
                        provider=provider,
                        role=role,
                        tsa_score=tsa_new,
                        iid_score=iid_new,
                        pvt_score=pvt_new,
                        efficiency_score=efficiency,
                        reputation_score=0.5,  # Inicial
                        total_turns=1
                    )
                    db.add(rep)
                else:
                    # Actualizar con EMA
                    a = self.ALPHA
                    rep.tsa_score = a * tsa_new + (1 - a) * rep.tsa_score
                    rep.iid_score = a * iid_new + (1 - a) * rep.iid_score
                    rep.pvt_score = a * pvt_new + (1 - a) * rep.pvt_score
                    rep.efficiency_score = a * efficiency + (1 - a) * rep.efficiency_score
                    rep.total_turns += 1
                
                # Recalcular score compuesto
                rep.reputation_score = (
                    rep.tsa_score * 0.3 +
                    rep.iid_score * 0.2 +
                    rep.pvt_score * 0.3 +
                    rep.efficiency_score * 0.2
                )
                rep.updated_at = datetime.utcnow()
                
                await db.commit()
                
                logger.debug(
                    'reputation.updated',
                    model=model,
                    role=role,
                    score=round(rep.reputation_score, 3),
                    turns=rep.total_turns
                )
                
        except Exception as e:
            # NUNCA propagar - solo loguear
            logger.error('reputation.update_failed', model=model, role=role, error=str(e))
    
    async def get_best_for_role(
        self,
        role: str,
        candidates: list,
        min_debates: int = 3
    ) -> Optional[str]:
        """
        Obtiene el mejor modelo para un rol basado en reputación.
        
        Args:
            role: Rol requerido
            candidates: Lista de modelos candidatos
            min_debates: Mínimo de debates para considerar
            
        Returns:
            Nombre del mejor modelo o None
        """
        if not get_settings().AGENT_REPUTATION_ENABLED:
            return None
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ModelReputation)
                    .where(
                        ModelReputation.role == role,
                        ModelReputation.model.in_(candidates),
                        ModelReputation.total_turns >= min_debates
                    )
                    .order_by(ModelReputation.reputation_score.desc())
                    .limit(1)
                )
                best = result.scalar_one_or_none()
                
                if best:
                    logger.info(
                        'reputation.best_selected',
                        model=best.model,
                        role=role,
                        score=round(best.reputation_score, 3)
                    )
                    return best.model
                
                return None
                
        except Exception as e:
            logger.error('reputation.get_best_failed', role=role, error=str(e))
            return None
    
    async def get_reputation(self, model: str, role: str) -> Optional[dict]:
        """
        Obtiene reputación de un modelo específico.
        
        Returns:
            Dict con scores o None
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ModelReputation)
                    .where(ModelReputation.model == model, ModelReputation.role == role)
                )
                rep = result.scalar_one_or_none()
                
                if rep:
                    return {
                        'model': rep.model,
                        'role': rep.role,
                        'tsa_score': round(rep.tsa_score, 3),
                        'iid_score': round(rep.iid_score, 3),
                        'pvt_score': round(rep.pvt_score, 3),
                        'efficiency_score': round(rep.efficiency_score, 3),
                        'reputation_score': round(rep.reputation_score, 3),
                        'total_turns': rep.total_turns,
                        'updated_at': rep.updated_at.isoformat() if rep.updated_at else None
                    }
                return None
                
        except Exception as e:
            logger.error('reputation.get_failed', model=model, role=role, error=str(e))
            return None
    
    async def list_all(self, min_turns: int = 1) -> list:
        """
        Lista todas las reputaciones.
        
        Returns:
            Lista de dicts con reputaciones
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ModelReputation)
                    .where(ModelReputation.total_turns >= min_turns)
                    .order_by(ModelReputation.reputation_score.desc())
                )
                reps = result.scalars().all()
                
                return [
                    {
                        'model': r.model,
                        'role': r.role,
                        'reputation_score': round(r.reputation_score, 3),
                        'total_turns': r.total_turns
                    }
                    for r in reps
                ]
                
        except Exception as e:
            logger.error('reputation.list_failed', error=str(e))
            return []


# Instancia global
reputation_manager = ReputationManager()
