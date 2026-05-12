"""
Synapse Council v2.0 - Sistema de Reputación Unificado (EMA)

Unifica los sistemas legacy:
- reputation.py: Análisis post-sesión con análisis de argumentos (AgentReputation)
- reputation_manager.py: Actualización por turno en tiempo real (ModelReputation)

Mantiene ModelReputation como modelo único de datos.
"""

import asyncio
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from backend.database.models import ModelReputation, AgentCall, Session
from backend.database.local_db import AsyncSessionLocal
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ReputationMetrics:
    """Métricas de reputación para un agente/modelo"""
    model: str
    provider: str
    role: str
    
    # Métricas calculadas
    tsa: float  # Tasa de Supervivencia de Argumentos (0-1)
    iid: float  # Índice de Independencia Dialéctica (0-1)
    pvt: float  # Precisión en Validación Técnica (0-1)
    efficiency: float  # Eficiencia (tokens/ms)
    
    # Datos para contexto
    total_turns: int
    successful_turns: int
    arguments_in_verdict: List[str]
    total_arguments: int


# ============================================================================
# CALCULADORES DE MÉTRICAS
# ============================================================================

class BaseMetricsCalculator(ABC):
    """Calculador base de métricas de reputación"""
    
    # Nota: No usamos @abstractmethod porque las subclases tienen diferentes firmas
    # TurnBasedCalculator usa calculate() con args específicos
    # SessionBasedCalculator usa calculate_for_session() con firma async diferente
    pass


class TurnBasedCalculator(BaseMetricsCalculator):
    """
    Calculador basado en turnos individuales.
    Usado por el sequential_debate_controller para actualizaciones en tiempo real.
    """
    
    def calculate(
        self,
        model: str,
        provider: str,
        role: str,
        tokens_out: int,
        latency_ms: float,
        success: bool,
        intervention_type: str = 'unknown'
    ) -> Dict[str, float]:
        """
        Calcula métricas basadas en un turno individual.
        
        Returns:
            Dict con tsa, iid, pvt, efficiency
        """
        # Efficiency: tokens por milisegundo, normalizado a 0-1
        efficiency = min((tokens_out / max(latency_ms, 1)) * 1000 / 10.0, 1.0)
        
        # TSA: Baja si el agente fue refutado
        tsa = 1.0 if intervention_type not in ['refutacion', 'refutation'] else 0.3
        
        # IID: Alta si hizo argumentos, críticas o refutaciones
        iid = 1.0 if intervention_type in ['argumento', 'refutacion', 'critica'] else 0.5
        
        # PVT: Basada en éxito del turno
        pvt = 1.0 if success else 0.0
        
        return {
            'tsa': tsa,
            'iid': iid,
            'pvt': pvt,
            'efficiency': efficiency
        }


class SessionBasedCalculator(BaseMetricsCalculator):
    """
    Calculador basado en análisis post-sesión completa.
    Usado por el session_manager para análisis de argumentos y veredicto.
    """
    
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
    
    def _extract_arguments(self, text: str) -> List[str]:
        """Extrae argumentos/puntos clave del texto"""
        if not text:
            return []
        
        arguments = []
        
        # Buscar bullets y números
        bullet_patterns = [
            r'^\s*[-•*]\s+(.+?)(?=\n|$)',
            r'^\s*\d+\.\s+(.+?)(?=\n|$)',
        ]
        
        for pattern in bullet_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                arg = match.group(1).strip()
                if len(arg) > 20:
                    arguments.append(arg[:200])
        
        # Buscar secciones ## Puntos Clave, ## Argumentos, etc.
        section_pattern = r'##?\s*(?:Puntos Clave|Argumentos|Key Points|Conclusiones)\s*:?\s*\n((?:.+\n)+?)(?=##|\Z)'
        section_match = re.search(section_pattern, text, re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            for line in section_text.split('\n'):
                line = line.strip()
                if line and len(line) > 20:
                    arguments.append(line[:200])
        
        return arguments[:20]  # Limitar a 20 argumentos
    
    def _argument_similarity(self, arg1: str, arg2: str) -> float:
        """Calcula similitud entre dos argumentos (Jaccard simple)"""
        words1 = set(arg1.lower().split())
        words2 = set(arg2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_tsa(
        self,
        agent_args: List[str],
        verdict_args: List[str]
    ) -> float:
        """
        TSA: Tasa de Supervivencia de Argumentos
        Qué % de argumentos del agente sobrevivieron al veredicto.
        """
        if not agent_args or not verdict_args:
            return 0.5  # Neutral si no hay datos
        
        survived = 0
        for agent_arg in agent_args:
            for verdict_arg in verdict_args:
                if self._argument_similarity(agent_arg, verdict_arg) > 0.6:
                    survived += 1
                    break
        
        return survived / len(agent_args)
    
    def _calculate_iid(self, role: str, responses: List[str]) -> float:
        """
        IID: Índice de Independencia Dialéctica
        Capacidad de divergir del consenso cuando es correcto.
        """
        if not responses:
            return 0.5
        
        # Roles críticos tienen mayor IID por definición
        role_lower = role.lower()
        if 'critic' in role_lower or 'crítico' in role_lower:
            base_iid = 0.7
        elif 'analyst' in role_lower or 'analista' in role_lower:
            base_iid = 0.5
        else:
            base_iid = 0.6
        
        # Analizar señales de pensamiento independiente
        independence_signals = 0
        signals = [
            r'no obstante', r'sin embargo', r'por el contrario',
            r'discrepo', r'objeción', r'crítica', r'falacia',
            r'falta evidencia', r'no está respaldado',
        ]
        
        for response in responses:
            for signal in signals:
                if re.search(signal, response, re.IGNORECASE):
                    independence_signals += 1
                    break
        
        adjustment = min(independence_signals * 0.05, 0.2)
        return min(base_iid + adjustment, 1.0)
    
    def _calculate_pvt(self, calls: List[AgentCall]) -> float:
        """
        PVT: Precisión en Validación Técnica
        Basado en señales de rigor técnico en las respuestas.
        """
        if not calls:
            return 0.5
        
        technical_signals = 0
        positive_signals = [
            r'dato', r'evidencia', r'estudio', r'fuente', r'referencia',
            r'cifra', r'porcentaje', r'estadística', r'caso de estudio',
            r'best practice',
        ]
        
        for call in calls:
            response = call.response or ""
            for signal in positive_signals:
                if re.search(signal, response, re.IGNORECASE):
                    technical_signals += 1
                    break
        
        return min(0.5 + (technical_signals / len(calls)) * 0.5, 1.0)
    
    async def calculate_for_session(
        self,
        session_id: str,
        db_session: AsyncSession
    ) -> Dict[str, ReputationMetrics]:
        """
        Calcula métricas para todos los modelos de una sesión.
        
        Returns:
            Dict[model_role_key, ReputationMetrics]
        """
        logger.info("reputation.session_calculating", session_id=session_id)
        
        # Obtener sesión y veredicto
        result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session or not session.tribunal_verdict:
            logger.warning("reputation.no_verdict", session_id=session_id)
            return {}
        
        # Extraer argumentos del veredicto
        verdict_text = ""
        if isinstance(session.tribunal_verdict, dict):
            verdict_text = session.tribunal_verdict.get("verdict_text", "")
        verdict_args = self._extract_arguments(verdict_text)
        
        # Obtener llamadas de agentes
        calls_result = await db_session.execute(
            select(AgentCall).where(
                AgentCall.session_id == session_id,
                AgentCall.status == "COMPLETED"
            )
        )
        calls = calls_result.scalars().all()
        
        if not calls:
            logger.warning("reputation.no_calls", session_id=session_id)
            return {}
        
        # Agrupar por modelo
        model_data: Dict[str, Dict] = {}
        for call in calls:
            if call.phase not in ["ANALYSIS", "CRITIQUE", "NODE_SYNTHESIS"]:
                continue
            
            key = f"{call.model_name}:{call.role_label}"
            
            if key not in model_data:
                model_data[key] = {
                    'model': call.model_name,
                    'engine': call.engine,
                    'role': call.role_label,
                    'responses': [],
                    'arguments': [],
                    'call_count': 0,
                    'tokens_out': 0,
                }
            
            model_data[key]['responses'].append(call.response or "")
            model_data[key]['arguments'].extend(
                self._extract_arguments(call.response or "")
            )
            model_data[key]['call_count'] += 1
            model_data[key]['tokens_out'] += call.tokens_out or 0
        
        # Calcular métricas por modelo
        metrics = {}
        for key, data in model_data.items():
            tsa = self._calculate_tsa(data['arguments'], verdict_args)
            iid = self._calculate_iid(data['role'], data['responses'])
            pvt = self._calculate_pvt([
                c for c in calls 
                if c.model_name == data['model'] and c.role_label == data['role']
            ])
            
            # Efficiency: promedio basado en tokens
            efficiency = 0.5  # Valor por defecto
            
            metrics[key] = ReputationMetrics(
                model=data['model'],
                provider=data['engine'],
                role=data['role'],
                tsa=tsa,
                iid=iid,
                pvt=pvt,
                efficiency=efficiency,
                total_turns=data['call_count'],
                successful_turns=data['call_count'],
                arguments_in_verdict=[
                    arg for arg in data['arguments']
                    if any(self._argument_similarity(arg, v_arg) > 0.5 
                           for v_arg in verdict_args)
                ],
                total_arguments=len(data['arguments'])
            )
        
        logger.info(
            "reputation.session_calculated",
            session_id=session_id,
            models_evaluated=len(metrics)
        )
        
        return metrics


# ============================================================================
# REPUTATION SERVICE UNIFICADO
# ============================================================================

class ReputationService:
    """
    Servicio unificado de reputación.
    
    Combina:
    - Actualización por turno (TurnBasedCalculator)
    - Análisis post-sesión (SessionBasedCalculator)
    
    Usa ModelReputation como modelo único de datos.
    """
    
    # Factor EMA: 0.3 = últimos ~3 debates pesan 65%
    ALPHA = 0.3
    
    def __init__(self):
        self.turn_calculator = TurnBasedCalculator()
        self.session_calculator = SessionBasedCalculator(alpha=self.ALPHA)
    
    # -------------------------------------------------------------------------
    # MÉTODO 1: Actualización por Turno (para sequential_debate_controller)
    # -------------------------------------------------------------------------
    
    async def update_after_turn(
        self,
        model: str,
        provider: str,
        role: str,
        tokens_out: int,
        latency_ms: float,
        success: bool,
        intervention_type: str = 'unknown'
    ) -> None:
        """
        Actualiza reputación después de un turno individual.
        Siempre captura excepciones - nunca propaga errores.
        """
        if not settings.AGENT_REPUTATION_ENABLED:
            return
        
        try:
            # Calcular métricas del turno
            metrics = self.turn_calculator.calculate(
                model=model,
                provider=provider,
                role=role,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                success=success,
                intervention_type=intervention_type
            )
            
            async with AsyncSessionLocal() as db:
                # Buscar reputación existente
                result = await db.execute(
                    select(ModelReputation)
                    .where(
                        ModelReputation.model == model,
                        ModelReputation.role == role
                    )
                )
                rep = result.scalar_one_or_none()
                
                if rep is None:
                    # Crear nueva entrada
                    rep = ModelReputation(
                        model=model,
                        provider=provider,
                        role=role,
                        tsa_score=metrics['tsa'],
                        iid_score=metrics['iid'],
                        pvt_score=metrics['pvt'],
                        efficiency_score=metrics['efficiency'],
                        reputation_score=0.5,
                        total_turns=1,
                        total_debates=0
                    )
                    db.add(rep)
                else:
                    # Actualizar con EMA
                    a = self.ALPHA
                    rep.tsa_score = a * metrics['tsa'] + (1 - a) * rep.tsa_score
                    rep.iid_score = a * metrics['iid'] + (1 - a) * rep.iid_score
                    rep.pvt_score = a * metrics['pvt'] + (1 - a) * rep.pvt_score
                    rep.efficiency_score = a * metrics['efficiency'] + (1 - a) * rep.efficiency_score
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
                    'reputation.turn_updated',
                    model=model,
                    role=role,
                    score=round(rep.reputation_score, 3),
                    turns=rep.total_turns
                )
                
        except Exception as e:
            logger.error('reputation.turn_update_failed', model=model, role=role, error=str(e))
    
    # -------------------------------------------------------------------------
    # MÉTODO 2: Actualización Post-Sesión (para session_manager)
    # -------------------------------------------------------------------------
    
    async def update_after_session(
        self,
        session_id: str,
        db_session: AsyncSession
    ) -> None:
        """
        Actualiza reputación de todos los modelos tras completar sesión.
        Basado en análisis de argumentos y veredicto del tribunal.
        """
        if not settings.AGENT_REPUTATION_ENABLED:
            logger.info("reputation.disabled", session_id=session_id)
            return
        
        try:
            # Calcular métricas post-sesión
            metrics = await self.session_calculator.calculate_for_session(
                session_id, db_session
            )
            
            if not metrics:
                return
            
            # Actualizar cada modelo
            for key, metric in metrics.items():
                await self._update_model_reputation(metric, db_session)
            
            # Incrementar contador de debates para todos los modelos actualizados
            await db_session.execute(
                update(ModelReputation)
                .where(ModelReputation.model.in_([m.model for m in metrics.values()]))
                .values(total_debates=ModelReputation.total_debates + 1)
            )
            
            logger.info(
                "reputation.session_updated",
                session_id=session_id,
                models_updated=len(metrics)
            )
            
        except Exception as e:
            logger.error("reputation.session_update_failed", session_id=session_id, error=str(e))
    
    async def _update_model_reputation(
        self,
        metric: ReputationMetrics,
        db_session: AsyncSession
    ) -> None:
        """Actualiza registro EMA de un modelo"""
        # Buscar reputación existente
        result = await db_session.execute(
            select(ModelReputation).where(
                ModelReputation.model == metric.model,
                ModelReputation.role == metric.role
            )
        )
        existing = result.scalar_one_or_none()
        
        # Score compuesto basado en análisis de sesión
        composite = metric.tsa * 0.4 + metric.iid * 0.3 + metric.pvt * 0.3
        
        if existing:
            # Actualizar con EMA
            a = self.ALPHA
            existing.tsa_score = a * metric.tsa + (1 - a) * existing.tsa_score
            existing.iid_score = a * metric.iid + (1 - a) * existing.iid_score
            existing.pvt_score = a * metric.pvt + (1 - a) * existing.pvt_score
            # Efficiency se mantiene del cálculo por turno
            
            # Recalcular score compuesto
            existing.reputation_score = (
                existing.tsa_score * 0.3 +
                existing.iid_score * 0.2 +
                existing.pvt_score * 0.3 +
                existing.efficiency_score * 0.2
            )
            existing.total_turns += metric.total_turns
            existing.updated_at = datetime.utcnow()
            
        else:
            # Crear nuevo registro
            reputation = ModelReputation(
                model=metric.model,
                provider=metric.provider,
                role=metric.role,
                tsa_score=metric.tsa,
                iid_score=metric.iid,
                pvt_score=metric.pvt,
                efficiency_score=metric.efficiency,
                reputation_score=composite,
                total_turns=metric.total_turns,
                total_debates=1
            )
            db.add(reputation)
    
    # -------------------------------------------------------------------------
    # MÉTODOS DE CONSULTA
    # -------------------------------------------------------------------------
    
    async def get_reputation(self, model: str, role: str) -> Optional[Dict]:
        """Obtiene reputación de un modelo específico"""
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
                        'provider': rep.provider,
                        'tsa_score': round(rep.tsa_score, 3),
                        'iid_score': round(rep.iid_score, 3),
                        'pvt_score': round(rep.pvt_score, 3),
                        'efficiency_score': round(rep.efficiency_score, 3),
                        'reputation_score': round(rep.reputation_score, 3),
                        'total_turns': rep.total_turns,
                        'total_debates': rep.total_debates,
                        'updated_at': rep.updated_at.isoformat() if rep.updated_at else None
                    }
                return None
                
        except Exception as e:
            logger.error('reputation.get_failed', model=model, role=role, error=str(e))
            return None
    
    async def get_best_for_role(
        self,
        role: str,
        candidates: List[str],
        min_debates: int = 3
    ) -> Optional[str]:
        """
        Obtiene el mejor modelo para un rol basado en reputación.
        """
        if not settings.AGENT_REPUTATION_ENABLED:
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
    
    async def list_all(self, min_turns: int = 1) -> List[Dict]:
        """Lista todas las reputaciones"""
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
                        'provider': r.provider,
                        'reputation_score': round(r.reputation_score, 3),
                        'tsa_score': round(r.tsa_score, 3),
                        'iid_score': round(r.iid_score, 3),
                        'pvt_score': round(r.pvt_score, 3),
                        'efficiency_score': round(r.efficiency_score, 3),
                        'total_turns': r.total_turns,
                        'total_debates': r.total_debates
                    }
                    for r in reps
                ]
                
        except Exception as e:
            logger.error('reputation.list_failed', error=str(e))
            return []


# ============================================================================
# INSTANCIA GLOBAL (singleton pattern)
# ============================================================================

reputation_service = ReputationService()


# ============================================================================
# BACKWARDS COMPATIBILITY
# ============================================================================

class ReputationManager(ReputationService):
    """
    Alias para backwards compatibility con session_manager.py
    
    DEPRECATED: Usar reputation_service directamente
    """
    pass


# Instancia global legacy (para compatibilidad)
reputation_manager = reputation_service
