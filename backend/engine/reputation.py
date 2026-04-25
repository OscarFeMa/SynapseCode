"""
Synapse Council v2.0 - Sistema de Reputación por Méritos (EMA)

Implementa:
- EMA (Exponential Moving Average) para reputation_score
- TSA (Tasa de Supervivencia de Argumentos)
- IID (Índice de Independencia Dialéctica)
- PVT (Precisión en Validación Técnica)

Cálculo post-sesión para actualizar reputación de agentes.
"""
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.database.models import AgentCall, AgentReputation, Session
from backend.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# El Alpha para EMA se lee en tiempo de ejecución de settings


@dataclass
class ReputationMetrics:
    """Métricas de reputación para un agente"""
    agent_slot: str
    model_name: str
    engine: str
    domain: str
    
    # Métricas calculadas
    tsa: float  # Tasa de Supervivencia de Argumentos (0-1)
    iid: float  # Índice de Independencia Dialéctica (0-1)
    pvt: float  # Precisión en Validación Técnica (0-1)
    
    # Datos para contexto
    total_calls: int
    successful_calls: int
    arguments_in_verdict: List[str]
    total_arguments: int


class ReputationCalculator:
    """
    Calculador de métricas de reputación post-sesión.
    Evalúa contribución de cada agente al veredicto final.
    """
    
    @property
    def alpha(self) -> float:
        return settings.REPUTATION_EMA_ALPHA
    
    async def calculate_session_reputation(
        self,
        session_id: str,
        db_session: AsyncSession
    ) -> Dict[str, ReputationMetrics]:
        """
        Calcula métricas de reputación para todos los agentes de una sesión.
        """
        logger.info("reputation.calculating", session_id=session_id)
        
        # Obtener sesión y veredicto
        result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session or not session.tribunal_verdict:
            logger.warning("reputation.no_verdict", session_id=session_id)
            return {}
        
        # Obtener todas las llamadas de agentes
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
        
        # Extraer argumentos del veredicto final
        verdict_text = ""
        if isinstance(session.tribunal_verdict, dict):
            verdict_text = session.tribunal_verdict.get("verdict_text", "")
        
        verdict_arguments = self._extract_arguments(verdict_text)
        
        # Calcular métricas por agente
        metrics = {}
        for call in calls:
            if call.phase not in ["ANALYSIS", "CRITIQUE", "NODE_SYNTHESIS"]:
                continue  # Solo fases productivas
            
            agent_id = f"{call.agent_slot}:{call.model_name}"
            
            if agent_id not in metrics:
                metrics[agent_id] = {
                    "agent_slot": call.agent_slot,
                    "model_name": call.model_name,
                    "engine": call.engine,
                    "domain": self._detect_domain(call.phase, call.role_label),
                    "responses": [],
                    "arguments_list": [],
                    "call_count": 0,
                    "token_count": 0,
                }
            
            metrics[agent_id]["responses"].append(call.response or "")
            metrics[agent_id]["arguments_list"].extend(
                self._extract_arguments(call.response or "")
            )
            metrics[agent_id]["call_count"] += 1
            metrics[agent_id]["token_count"] += call.tokens_out or 0
        
        # Calcular métricas finales
        result = {}
        for agent_id, data in metrics.items():
            # TSA: Qué % de argumentos del agente aparecen en el veredicto
            tsa = self._calculate_tsa(data["arguments_list"], verdict_arguments)
            
            # IID: Capacidad de divergir del consenso (basado en críticas)
            iid = self._calculate_iid(data["agent_slot"], data["responses"])
            
            # PVT: Precisión técnica (basado en críticas recibidas)
            pvt = await self._calculate_pvt(
                session_id, data["agent_slot"], db_session
            )
            
            rep_metrics = ReputationMetrics(
                agent_slot=data["agent_slot"],
                model_name=data["model_name"],
                engine=data["engine"],
                domain=data["domain"],
                tsa=tsa,
                iid=iid,
                pvt=pvt,
                total_calls=data["call_count"],
                successful_calls=data["call_count"],  # Solo exitosas
                arguments_in_verdict=[
                    arg for arg in data["arguments_list"]
                    if any(self._argument_similarity(arg, v_arg) > 0.5 
                           for v_arg in verdict_arguments)
                ],
                total_arguments=len(data["arguments_list"])
            )
            
            result[agent_id] = rep_metrics
        
        logger.info(
            "reputation.calculated",
            session_id=session_id,
            agents_evaluated=len(result)
        )
        
        return result
    
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
                if len(arg) > 20:  # Ignorar líneas muy cortas
                    arguments.append(arg[:200])  # Truncar muy largos
        
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
    
    def _calculate_tsa(self, agent_args: List[str], verdict_args: List[str]) -> float:
        """
        TSA: Tasa de Supervivencia de Argumentos
        Qué porcentaje de argumentos del agente sobrevivieron al veredicto.
        """
        if not agent_args:
            return 0.5  # Neutral si no hay argumentos
        
        if not verdict_args:
            return 0.5
        
        survived = 0
        for agent_arg in agent_args:
            # Si es similar a algún argumento del veredicto, sobrevivió
            for verdict_arg in verdict_args:
                if self._argument_similarity(agent_arg, verdict_arg) > 0.6:
                    survived += 1
                    break
        
        return survived / len(agent_args)
    
    def _calculate_iid(self, agent_slot: str, responses: List[str]) -> float:
        """
        IID: Índice de Independencia Dialéctica
        Capacidad del agente para divergir del consenso cuando es correcto.
        Basado en la cantidad y calidad de críticas emitidas.
        """
        if not responses:
            return 0.5
        
        # Críticos tienen mayor IID por definición
        if "critic" in agent_slot:
            base_iid = 0.7
        elif "analyst" in agent_slot:
            base_iid = 0.5
        else:
            base_iid = 0.6
        
        # Analizar respuestas por señales de pensamiento independiente
        independence_signals = 0
        for response in responses:
            # Señales de pensamiento crítico
            signals = [
                r'no obstante',
                r'sin embargo',
                r'por el contrario',
                r'discrepo',
                r'objeción',
                r'crítica',
                r'falacia',
                r'falta evidencia',
                r'no está respaldado',
            ]
            for signal in signals:
                if re.search(signal, response, re.IGNORECASE):
                    independence_signals += 1
                    break
        
        # Ajustar según señales encontradas
        adjustment = min(independence_signals * 0.05, 0.2)
        return min(base_iid + adjustment, 1.0)
    
    async def _calculate_pvt(
        self,
        session_id: str,
        agent_slot: str,
        db_session: AsyncSession
    ) -> float:
        """
        PVT: Precisión en Validación Técnica
        Basado en críticas recibidas por el Magistrado de Evidencias.
        """
        # Buscar llamadas de este agente
        result = await db_session.execute(
            select(AgentCall).where(
                AgentCall.session_id == session_id,
                AgentCall.agent_slot == agent_slot,
                AgentCall.status == "COMPLETED"
            )
        )
        calls = result.scalars().all()
        
        if not calls:
            return 0.5
        
        # Analizar respuestas por señales de rigor técnico
        technical_signals = 0
        for call in calls:
            response = call.response or ""
            
            # Señales de rigor técnico
            positive_signals = [
                r'dato',
                r'evidencia',
                r'estudio',
                r'fuente',
                r'referencia',
                r'cifra',
                r'porcentaje',
                r'estadística',
                r'caso de estudio',
                r'best practice',
            ]
            
            for signal in positive_signals:
                if re.search(signal, response, re.IGNORECASE):
                    technical_signals += 1
                    break
        
        return min(0.5 + (technical_signals / len(calls)) * 0.5, 1.0)
    
    def _argument_similarity(self, arg1: str, arg2: str) -> float:
        """Calcula similitud entre dos argumentos (simple Jaccard)"""
        words1 = set(arg1.lower().split())
        words2 = set(arg2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _detect_domain(self, phase: str, role_label: str) -> str:
        """Detecta dominio de especialización del agente"""
        role_lower = role_label.lower()
        
        if "técnico" in role_lower or "técnica" in role_lower:
            return "technical"
        elif "estratégico" in role_lower or "strategy" in role_lower:
            return "strategy"
        elif "riesgo" in role_lower or "risk" in role_lower:
            return "security"
        elif "empírico" in role_lower or "empirical" in role_lower:
            return "technical"
        elif "organizacional" in role_lower or "human" in role_lower:
            return "creative"
        
        return "general"


class ReputationManager:
    """
    Gestor de reputación.
    Actualiza scores en base de datos después de cada sesión.
    """
    
    def __init__(self):
        self.calculator = ReputationCalculator()
    
    async def update_reputation_after_session(
        self,
        session_id: str,
        db_session: AsyncSession
    ):
        """
        Actualiza reputación de todos los agentes tras completar sesión.
        """
        if not settings.AGENT_REPUTATION_ENABLED:
            logger.info("reputation.disabled", session_id=session_id)
            return
        
        # Calcular métricas
        metrics = await self.calculator.calculate_session_reputation(
            session_id, db_session
        )
        
        if not metrics:
            return
        
        # Actualizar o crear registros de reputación
        for agent_id, metric in metrics.items():
            await self._update_agent_reputation(metric, db_session)
        
        logger.info(
            "reputation.updated",
            session_id=session_id,
            agents_updated=len(metrics)
        )
    
    async def _update_agent_reputation(
        self,
        metric: ReputationMetrics,
        db_session: AsyncSession
    ):
        """Actualiza registro EMA de un agente"""
        # Buscar reputación existente
        result = await db_session.execute(
            select(AgentReputation).where(
                AgentReputation.agent_slot == metric.agent_slot,
                AgentReputation.model_name == metric.model_name,
                AgentReputation.domain == metric.domain
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Actualizar con EMA
            old_score = existing.reputation_score
            
            # Nuevo score ponderado
            new_score = (
                self.calculator.alpha * self._composite_score(metric) +
                (1 - self.calculator.alpha) * old_score
            )
            
            existing.reputation_score = round(new_score, 3)
            existing.argument_survival_rate = round(metric.tsa, 3)
            existing.dialectic_independence = round(metric.iid, 3)
            existing.technical_precision = round(metric.pvt, 3)
            existing.total_debates += 1
            existing.last_updated = datetime.utcnow()
            
        else:
            # Crear nuevo registro
            reputation = AgentReputation(
                id=str(uuid.uuid4()),
                agent_slot=metric.agent_slot,
                model_name=metric.model_name,
                engine=metric.engine,
                domain=metric.domain,
                reputation_score=round(self._composite_score(metric), 3),
                argument_survival_rate=round(metric.tsa, 3),
                dialectic_independence=round(metric.iid, 3),
                technical_precision=round(metric.pvt, 3),
                total_debates=1,
                last_updated=datetime.utcnow(),
            )
            db_session.add(reputation)
    
    def _composite_score(self, metric: ReputationMetrics) -> float:
        """Calcula score compuesto ponderado"""
        # Pesos: TSA 40%, IID 30%, PVT 30%
        return (
            metric.tsa * 0.4 +
            metric.iid * 0.3 +
            metric.pvt * 0.3
        )
    
    async def get_agent_reputation(
        self,
        agent_slot: str,
        model_name: str,
        domain: str,
        db_session: AsyncSession
    ) -> Optional[AgentReputation]:
        """Obtiene reputación de un agente específico"""
        result = await db_session.execute(
            select(AgentReputation).where(
                AgentReputation.agent_slot == agent_slot,
                AgentReputation.model_name == model_name,
                AgentReputation.domain == domain
            )
        )
        return result.scalar_one_or_none()
    
    async def get_top_agents(
        self,
        domain: str,
        db_session: AsyncSession,
        limit: int = 5
    ) -> List[AgentReputation]:
        """Obtiene top agents por dominio"""
        result = await db_session.execute(
            select(AgentReputation)
            .where(AgentReputation.domain == domain)
            .order_by(AgentReputation.reputation_score.desc())
            .limit(limit)
        )
        return result.scalars().all()
