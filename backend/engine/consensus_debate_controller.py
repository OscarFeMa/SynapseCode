"""
Synapse Council v2.0 - Consensus Debate Controller
Sistema de consenso multi-modelo con validación cruzada y detección de sesgos
"""
import asyncio
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.engine.local_engine_manager import LocalEngineManager, EngineType
from backend.adapters.openrouter import OpenRouterClient
from backend.config import get_settings
from backend.database.local_db import AsyncSessionLocal
from backend.database.models import ConsensusDebate, ConsensusRound as ConsensusRoundModel, ConsensusAgentPosition
from backend.services.supabase_sync import SupabaseSyncService
from backend.engine.sequential_debate_controller import AgentRole, DebateAgent, TRANSCRIPTS_DIR

settings = get_settings()
logger = structlog.get_logger()


class ConsensusStatus(Enum):
    """Estados del proceso de consenso"""
    PROPOSAL = "proposal"           # Ronda 1: Propuestas iniciales
    REFUTATION = "refutation"         # Ronda 2: Refutación cruzada
    SYNTHESIS = "synthesis"           # Ronda 3: Síntesis de puntos válidos
    VALIDATION = "validation"       # Ronda 4: Validación lógica
    CONVERGENCE = "convergence"     # Ronda 5+: Negociación hasta convergencia
    CONSENSUS_REACHED = "consensus_reached"
    CONSENSUS_FAILED = "consensus_failed"
    DISAGREEMENT_PERSISTENT = "disagreement_persistent"


@dataclass
class AgentPosition:
    """Posición de un agente en el debate"""
    agent: DebateAgent
    position: str = ""                    # Argumento principal
    confidence: float = 0.0               # 0-1 confianza en posición
    supporting_points: List[str] = field(default_factory=list)
    objections_raised: List[str] = field(default_factory=list)
    responses_to_objections: Dict[int, str] = field(default_factory=dict)  # turn -> response
    logical_fallacies_detected: List[Dict[str, Any]] = field(default_factory=list)
    consensus_score: float = 0.0          # Qué tan alineado con consenso final


@dataclass
class CrossValidation:
    """Validación cruzada entre dos agentes"""
    evaluator_agent: str
    evaluated_agent: str
    validation_score: float             # 0-1 validez de argumentos
    identified_fallacies: List[str]
    agreement_level: float                # 0-1 nivel de acuerdo
    constructive_feedback: str


@dataclass
class ConsensusRoundData:
    """Una ronda del debate de consenso (dataclass interno)"""
    round_number: int
    round_type: ConsensusStatus
    positions: Dict[str, AgentPosition] = field(default_factory=dict)  # agent_id -> position
    validations: List[CrossValidation] = field(default_factory=list)
    global_consensus_score: float = 0.0   # Métrica de consenso grupal
    dissent_topics: List[str] = field(default_factory=list)
    converged: bool = False


@dataclass
class ConsensusSession:
    """Sesión completa de debate de consenso"""
    id: str
    topic: str
    status: str = "created"
    agents: List[DebateAgent] = field(default_factory=list)
    rounds: List[ConsensusRoundData] = field(default_factory=list)
    final_consensus: Optional[str] = None
    consensus_score: float = 0.0          # Score final 0-1
    bias_analysis: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    transcript_path: Optional[str] = None
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: int = 0


class ConsensusDebateController:
    """
    Controller para debates de consenso multi-modelo.
    
    Implementa:
    - Rondas iterativas de propuesta-refutación-síntesis
    - Validación cruzada entre todos los agentes
    - Detección de sesgos y falacias lógicas
    - Convergencia hasta consenso o máximo de rondas
    """
    
    def __init__(self):
        self.local_manager = LocalEngineManager()
        self.openrouter = None
        if settings.OPENROUTER_API_KEY:
            self.openrouter = OpenRouterClient(api_key=settings.OPENROUTER_API_KEY)
        self.supabase_sync = SupabaseSyncService()
        self.active_sessions: Dict[str, ConsensusSession] = {}
        
        # Umbrales de consenso
        self.CONSENSUS_THRESHOLD = 0.75       # 75% acuerdo = consenso
        self.DISSENT_THRESHOLD = 0.30         # 30% disenso = requiere otra ronda
        self.MAX_ROUNDS = 5
        
    async def create_consensus_debate(
        self,
        topic: str,
        agents_config: List[DebateAgent],
        on_round_complete: Optional[Callable[[ConsensusRoundData], None]] = None,
        on_consensus_update: Optional[Callable[[float, str], None]] = None
    ) -> ConsensusSession:
        """Crea y ejecuta un debate de consenso con ID autogenerado"""
        session_id = str(uuid.uuid4())
        return await self.create_consensus_debate_with_id(
            session_id=session_id,
            topic=topic,
            agents_config=agents_config,
            on_round_complete=on_round_complete,
            on_consensus_update=on_consensus_update
        )

    async def create_consensus_debate_with_id(
        self,
        session_id: str,
        topic: str,
        agents_config: List[DebateAgent],
        on_round_complete: Optional[Callable[[ConsensusRoundData], None]] = None,
        on_consensus_update: Optional[Callable[[float, str], None]] = None
    ) -> ConsensusSession:
        """Crea y ejecuta un debate de consenso con ID proporcionado"""
        
        logger.info("consensus_debate.starting",
                   session_id=session_id,
                   topic=topic,
                   agents_count=len(agents_config))
        
        session = ConsensusSession(
            id=session_id,
            topic=topic,
            agents=agents_config
        )
        self.active_sessions[session_id] = session
        
        # Crear registro en BD
        try:
            async with AsyncSessionLocal() as db_session:
                db_debate = ConsensusDebate(
                    id=session_id,
                    topic=topic,
                    status="running",
                    total_agents=len(agents_config),
                    max_rounds=self.MAX_ROUNDS
                )
                db_session.add(db_debate)
                await db_session.commit()
        except Exception as e:
            logger.error("consensus_debate.db_create_error", error=str(e))
        
        try:
            # RONDA 1: PROPUESTAS INICIALES
            logger.info("consensus_debate.round_1_proposals")
            round_1 = await self._run_proposal_round(session, agents_config)
            session.rounds.append(round_1)
            
            if on_round_complete:
                on_round_complete(round_1)
            
            # Calcular consenso inicial
            initial_consensus = self._calculate_consensus_score(round_1.positions)
            logger.info("consensus_debate.initial_score", score=initial_consensus)
            
            # RONDA 2: REFUTACIÓN CRUZADA
            logger.info("consensus_debate.round_2_refutation")
            round_2 = await self._run_refutation_round(session, round_1)
            session.rounds.append(round_2)
            
            if on_round_complete:
                on_round_complete(round_2)
            
            # RONDA 3: SÍNTESIS
            logger.info("consensus_debate.round_3_synthesis")
            round_3 = await self._run_synthesis_round(session, round_2)
            session.rounds.append(round_3)
            
            if on_round_complete:
                on_round_complete(round_3)
            
            # Evaluar convergencia
            current_consensus = round_3.global_consensus_score
            current_round = 3
            
            # RONDAS 4+: CONVERGENCIA (si es necesario)
            while (current_consensus < self.CONSENSUS_THRESHOLD and 
                   current_round < self.MAX_ROUNDS and
                   len(round_3.dissent_topics) > 0):
                
                current_round += 1
                logger.info("consensus_debate.convergence_round",
                           round=current_round,
                           current_score=current_consensus)
                
                convergence_round = await self._run_convergence_round(
                    session, session.rounds[-1], current_round
                )
                session.rounds.append(convergence_round)
                current_consensus = convergence_round.global_consensus_score
                
                if on_round_complete:
                    on_round_complete(convergence_round)
                
                if on_consensus_update:
                    status = "converging" if current_consensus < self.CONSENSUS_THRESHOLD else "reached"
                    on_consensus_update(current_consensus, status)
                
                if convergence_round.converged:
                    break
            
            # Generar consenso final
            session.consensus_score = current_consensus
            session.final_consensus = await self._generate_final_consensus(session)
            
            # Análisis de sesgos
            session.bias_analysis = self._analyze_biases(session)
            
            # Determinar estado final
            if current_consensus >= self.CONSENSUS_THRESHOLD:
                session.status = "consensus_reached"
            elif current_round >= self.MAX_ROUNDS:
                session.status = "max_rounds_reached"
            else:
                session.status = "partial_consensus"
            
            session.completed_at = datetime.now()
            
            # Guardar transcripción
            transcript_path = await self._save_consensus_transcript(session)
            session.transcript_path = transcript_path
            
            # Actualizar BD
            await self._persist_consensus_to_db(session)
            
            logger.info("consensus_debate.completed",
                       session_id=session_id,
                       rounds=current_round,
                       consensus_score=current_consensus,
                       status=session.status)
            
        except Exception as e:
            session.status = "failed"
            logger.error("consensus_debate.failed",
                        session_id=session_id,
                        error=str(e))
            raise
        
        return session
    
    async def _run_proposal_round(
        self,
        session: ConsensusSession,
        agents: List[DebateAgent]
    ) -> ConsensusRoundData:
        """
        Ronda 1: Cada agente presenta su posición inicial sobre el tema.
        """
        round_data = ConsensusRoundData(
            round_number=1,
            round_type=ConsensusStatus.PROPOSAL
        )
        
        # Ejecutar todos los agentes en paralelo para propuestas (con reintentos y fallback)
        tasks = []
        for agent in agents:
            task = self._generate_agent_proposal_with_retry(session, agent)
            tasks.append(task)
        
        positions = await asyncio.gather(*tasks)
        
        for agent, position in zip(agents, positions):
            if isinstance(position, Exception):
                logger.error("consensus.proposal_failed_unexpected",
                           agent=agent.name,
                           error=str(position))
                # Esto no debería pasar porque _with_retry maneja excepciones
                position = AgentPosition(
                    agent=agent,
                    position=f"[Error inesperado: {str(position)[:100]}]",
                    confidence=0.0
                )
            
            round_data.positions[agent.id] = position
        
        # Calcular consenso inicial
        round_data.global_consensus_score = self._calculate_consensus_score(round_data.positions)
        
        return round_data
    
    async def _generate_agent_proposal_with_retry(
        self,
        session: ConsensusSession,
        agent: DebateAgent,
        max_retries: int = 2
    ) -> AgentPosition:
        """Genera posición con reintentos y fallback entre modelos"""
        
        # Modelos fallback por si el principal falla
        fallback_models = ["llama3.2:latest", "mistral:7b", "qwen2.5:3b"]
        
        last_error = None
        
        # Intentar con el modelo principal primero
        for attempt in range(max_retries + 1):
            try:
                logger.info("consensus.proposal_attempt",
                           agent=agent.name,
                           model=agent.model,
                           attempt=attempt + 1,
                           max_attempts=max_retries + 1)
                
                position = await self._generate_agent_proposal_once(session, agent)
                
                # Verificar que la posición es válida
                if position.position and not position.position.startswith("["):
                    logger.info("consensus.proposal_success",
                               agent=agent.name,
                               model=agent.model,
                               confidence=position.confidence)
                    return position
                else:
                    logger.warning("consensus.proposal_empty",
                                  agent=agent.name,
                                  position=position.position[:50])
                    
            except Exception as e:
                last_error = e
                logger.error("consensus.proposal_attempt_failed",
                           agent=agent.name,
                           model=agent.model,
                           attempt=attempt + 1,
                           error=str(e),
                           error_type=type(e).__name__)
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s
                    logger.info("consensus.proposal_retrying",
                               agent=agent.name,
                               wait_seconds=wait_time)
                    await asyncio.sleep(wait_time)
        
        # Si falló el modelo principal, intentar con modelos fallback
        for fallback_model in fallback_models:
            if fallback_model == agent.model:
                continue  # Ya intentamos este
                
            try:
                logger.info("consensus.proposal_fallback",
                           agent=agent.name,
                           original_model=agent.model,
                           fallback_model=fallback_model)
                
                # Crear agente temporal con modelo fallback
                fallback_agent = DebateAgent(
                    id=f"{agent.id}_fallback",
                    name=f"{agent.name} (fallback)",
                    model=fallback_model,
                    role=agent.role,
                    system_prompt=agent.system_prompt,
                    temperature=agent.temperature,
                    provider=EngineType.OLLAMA,
                    node="LOCAL"
                )
                
                position = await self._generate_agent_proposal_once(session, fallback_agent)
                
                if position.position and not position.position.startswith("["):
                    # Actualizar el agente referenciado en la posición
                    position.agent = agent
                    logger.info("consensus.proposal_fallback_success",
                               agent=agent.name,
                               fallback_model=fallback_model)
                    return position
                    
            except Exception as e:
                logger.error("consensus.proposal_fallback_failed",
                           agent=agent.name,
                           fallback_model=fallback_model,
                           error=str(e))
                continue
        
        # Si todo falló, crear posición de error pero con información útil
        logger.error("consensus.proposal_all_failed",
                    agent=agent.name,
                    original_model=agent.model,
                    last_error=str(last_error) if last_error else "unknown")
        
        return AgentPosition(
            agent=agent,
            position=f"[Error tras {max_retries + 1} intentos: {str(last_error)[:100]}...]",
            confidence=0.0,
            consensus_score=0.0
        )
    
    async def _generate_agent_proposal_once(
        self,
        session: ConsensusSession,
        agent: DebateAgent
    ) -> AgentPosition:
        """Genera la posición inicial de un agente (una sola vez)"""
        
        prompt = f"""# DEBATE DE CONSENSO

## Tema
{session.topic}

## Tu Rol
Eres: {agent.name}
Rol: {agent.role.value}
Modelo: {agent.model}

## Tu Tarea
Presenta tu posición inicial sobre el tema de manera clara, estructurada y fundamentada.

Debes incluir:
1. **Posición principal**: Tu stance claro (sí/no/condicional)
2. **Argumentos clave**: 2-3 puntos fundamentales con evidencia lógica
3. **Confianza**: Qué tan seguro estás de tu posición (0-100%)
4. **Premisas**: Supuestos base de tu argumentación

## Formato de Respuesta
**POSICIÓN**: [Sí/No/Condicional - explica condiciones]

**ARGUMENTOS**:
1. [Argumento 1 con fundamento lógico]
2. [Argumento 2 con fundamento lógico]
3. [Argumento 3 opcional]

**CONFIANZA**: [0-100]%

**PREMISAS CLAVE**:
- [Premisa 1]
- [Premisa 2]

Máximo 400 palabras. Sé riguroso y preciso.
"""

        start_time = datetime.now()
        response_parts = []
        tokens_out = 0
        
        try:
            async for token in self._call_agent(agent, prompt):
                response_parts.append(token)
                tokens_out += 1
            
            response = "".join(response_parts)
            latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Verificar que la respuesta no está vacía
            if not response or len(response.strip()) < 50:
                raise ValueError(f"Respuesta vacía o muy corta ({len(response) if response else 0} chars)")
            
            # Parsear respuesta
            position = self._parse_proposal_response(agent, response)
            
            # Actualizar métricas de sesión
            session.total_tokens_out += tokens_out
            session.total_latency_ms += latency_ms
            
            return position
            
        except Exception as e:
            logger.error("consensus.proposal_once_error",
                        agent=agent.name,
                        error=str(e),
                        error_type=type(e).__name__)
            raise  # Re-lanzar para que el reintentador lo maneje
    
    def _parse_proposal_response(self, agent: DebateAgent, response: str) -> AgentPosition:
        """Parsea la respuesta de propuesta del agente"""
        position = AgentPosition(agent=agent)
        
        # Extraer posición principal
        if "**POSICIÓN**:" in response:
            pos_start = response.find("**POSICIÓN**:") + 14
            pos_end = response.find("\n\n", pos_start)
            if pos_end == -1:
                pos_end = len(response)
            position.position = response[pos_start:pos_end].strip()
        else:
            position.position = response[:200] + "..."
        
        # Extraer confianza
        import re
        confidence_match = re.search(r'\*\*CONFIANZA\*\*:\s*(\d+)%', response)
        if confidence_match:
            position.confidence = int(confidence_match.group(1)) / 100.0
        else:
            # Buscar número cercano a %
            alt_match = re.search(r'(\d+)%', response)
            if alt_match:
                position.confidence = int(alt_match.group(1)) / 100.0
        
        # Extraer puntos de apoyo
        if "**ARGUMENTOS**:" in response:
            args_section = response.split("**ARGUMENTOS**:")[1].split("**")[0]
            points = [p.strip() for p in args_section.split('\n') if p.strip().startswith('-') or p.strip().startswith('1.') or p.strip().startswith('2.') or p.strip().startswith('3.')]
            position.supporting_points = points[:3]
        
        return position
    
    async def _run_refutation_round(
        self,
        session: ConsensusSession,
        previous_round: ConsensusRoundData
    ) -> ConsensusRoundData:
        """
        Ronda 2: Cada agente evalúa y refuta las posiciones de los otros agentes.
        Implementa validación cruzada completa.
        """
        round_data = ConsensusRoundData(
            round_number=2,
            round_type=ConsensusStatus.REFUTATION
        )
        
        positions = previous_round.positions
        agent_ids = list(positions.keys())
        
        # Cada agente evalúa a todos los demás
        validations = []
        
        for evaluator_id in agent_ids:
            evaluator = positions[evaluator_id].agent
            
            for evaluated_id in agent_ids:
                if evaluator_id == evaluated_id:
                    continue  # No auto-evaluación
                
                evaluated_position = positions[evaluated_id]
                
                # Generar validación cruzada con reintentos
                validation = await self._generate_cross_validation_with_retry(
                    session, evaluator, evaluated_position
                )
                validations.append(validation)
                
                # Almacenar objeciones en la posición evaluada
                if validation.identified_fallacies:
                    positions[evaluated_id].objections_raised.extend(
                        validation.identified_fallacies
                    )
                
                # Almacenar falacias detectadas
                if validation.identified_fallacies:
                    for fallacy in validation.identified_fallacies:
                        positions[evaluated_id].logical_fallacies_detected.append({
                            "detected_by": evaluator.name,
                            "fallacy": fallacy,
                            "round": 2
                        })
        
        round_data.validations = validations
        round_data.positions = positions
        
        # Recalcular consenso tras refutaciones
        round_data.global_consensus_score = self._calculate_consensus_score(
            positions, validations
        )
        
        # Identificar temas de disenso
        round_data.dissent_topics = self._identify_dissent_topics(validations)
        
        return round_data
    
    async def _generate_cross_validation_with_retry(
        self,
        session: ConsensusSession,
        evaluator: DebateAgent,
        evaluated: AgentPosition,
        max_retries: int = 2
    ) -> CrossValidation:
        """Genera validación cruzada con reintentos"""
        
        for attempt in range(max_retries + 1):
            try:
                logger.info("consensus.validation_attempt",
                           evaluator=evaluator.name,
                           evaluated=evaluated.agent.name,
                           attempt=attempt + 1)
                
                validation = await self._generate_cross_validation_once(
                    session, evaluator, evaluated
                )
                
                # Verificar que no es un error
                if not validation.constructive_feedback.startswith("["):
                    logger.info("consensus.validation_success",
                               evaluator=evaluator.name,
                               evaluated=evaluated.agent.name,
                               agreement=validation.agreement_level)
                    return validation
                    
            except Exception as e:
                logger.error("consensus.validation_attempt_failed",
                           evaluator=evaluator.name,
                           evaluated=evaluated.agent.name,
                           attempt=attempt + 1,
                           error=str(e))
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info("consensus.validation_retrying",
                               wait_seconds=wait_time)
                    await asyncio.sleep(wait_time)
        
        # Si todo falló, retornar validación neutral con info del error
        logger.error("consensus.validation_all_failed",
                    evaluator=evaluator.name,
                    evaluated=evaluated.agent.name)
        
        return CrossValidation(
            evaluator_agent=evaluator.name,
            evaluated_agent=evaluated.agent.name,
            validation_score=0.5,  # Neutral
            identified_fallacies=["[Validación falló tras múltiples intentos]"],
            agreement_level=0.5,  # Neutral
            constructive_feedback="[No se pudo completar la validación debido a errores de conexión con el modelo]"
        )
    
    async def _generate_cross_validation_once(
        self,
        session: ConsensusSession,
        evaluator: DebateAgent,
        evaluated: AgentPosition
    ) -> CrossValidation:
        """Genera una validación cruzada de un agente sobre otro (una vez)"""
        
        # Verificar que la posición a evaluar no está vacía
        if not evaluated.position or evaluated.position.startswith("["):
            logger.warning("consensus.validation_empty_position",
                          evaluator=evaluator.name,
                          evaluated=evaluated.agent.name,
                          position=evaluated.position[:50] if evaluated.position else "None")
            return CrossValidation(
                evaluator_agent=evaluator.name,
                evaluated_agent=evaluated.agent.name,
                validation_score=0.0,
                identified_fallacies=["[Posición vacía o con error - no se puede evaluar]"],
                agreement_level=0.0,
                constructive_feedback="El agente evaluado no proporcionó una posición válida para evaluar."
            )
        
        prompt = f"""# VALIDACIÓN CRUZADA

## Tema del Debate
{session.topic}

## Tu Rol
Eres: {evaluator.name} ({evaluator.role.value})
Evaluando a: {evaluated.agent.name}

## Posición a Evaluar
{evaluated.position}

## Puntos de Apoyo del Evaluado
{chr(10).join([f"- {p}" for p in evaluated.supporting_points]) if evaluated.supporting_points else "- [No se proporcionaron puntos de apoyo específicos]"}

## Tu Tarea
Realiza una validación cruzada rigurosa:

1. **Identifica falacias lógicas** (si existen):
   - Ad hominem, falso dilema, apelación a autoridad, etc.
   
2. **Evalúa validez de premisas**:
   - ¿Son consistentes? ¿Hay evidencia?
   
3. **Determina nivel de acuerdo** (0-100%):
   - ¿Coincides con la conclusión?
   
4. **Feedback constructivo**:
   - Qué argumentos son válidos vs débiles

## Formato de Respuesta
**FALACIAS IDENTIFICADAS**:
- [Falacia 1: explicación]
- [Ninguna detectada / Otras]

**EVALUACIÓN DE PREMISAS**:
- Premisa 1: [Válida/Dudosa/Falsa] - razón
- Premisa 2: [Válida/Dudosa/Falsa] - razón

**NIVEL DE ACUERDO**: [0-100]%

**FEEDBACK CONSTRUCTIVO**:
[Puntos válidos identificados y debilidades constructivas]

Máximo 300 palabras. Sé objetivo y riguroso.
"""

        try:
            response_parts = []
            async for token in self._call_agent(evaluator, prompt):
                response_parts.append(token)
            
            response = "".join(response_parts)
            
            # Verificar que la respuesta no está vacía
            if not response or len(response.strip()) < 30:
                raise ValueError(f"Respuesta de validación vacía ({len(response) if response else 0} chars)")
            
            # Parsear validación
            validation = self._parse_validation_response(evaluator, evaluated, response)
            return validation
            
        except Exception as e:
            logger.error("consensus.validation_once_error",
                        evaluator=evaluator.name,
                        evaluated=evaluated.agent.name,
                        error=str(e))
            raise  # Re-lanzar para que el reintentador lo maneje
    
    def _parse_validation_response(
        self,
        evaluator: DebateAgent,
        evaluated: AgentPosition,
        response: str
    ) -> CrossValidation:
        """Parsea la respuesta de validación cruzada"""
        
        import re
        
        # Extraer nivel de acuerdo
        agreement = 0.5
        agreement_match = re.search(r'\*\*NIVEL DE ACUERDO\*\*:\s*(\d+)%', response)
        if agreement_match:
            agreement = int(agreement_match.group(1)) / 100.0
        
        # Extraer falacias
        fallacies = []
        if "**FALACIAS IDENTIFICADAS**:" in response:
            fal_section = response.split("**FALACIAS IDENTIFICADAS**:")[1].split("**")[0]
            for line in fal_section.split('\n'):
                line = line.strip()
                if line.startswith('-') and 'ninguna' not in line.lower():
                    fallacies.append(line[1:].strip())
        
        # Calcular score de validación
        validation_score = agreement
        if fallacies:
            validation_score *= 0.7  # Penalizar por falacias detectadas
        
        # Extraer feedback
        feedback = ""
        if "**FEEDBACK CONSTRUCTIVO**:" in response:
            fb_section = response.split("**FEEDBACK CONSTRUCTIVO**:")[1].strip()
            feedback = fb_section[:500]
        
        return CrossValidation(
            evaluator_agent=evaluator.name,
            evaluated_agent=evaluated.agent.name,
            validation_score=validation_score,
            identified_fallacies=fallacies,
            agreement_level=agreement,
            constructive_feedback=feedback
        )
    
    async def _run_synthesis_round(
        self,
        session: ConsensusSession,
        previous_round: ConsensusRoundData
    ) -> ConsensusRoundData:
        """
        Ronda 3: Síntesis de puntos válidos y generación de posiciones refinadas.
        """
        round_data = ConsensusRoundData(
            round_number=3,
            round_type=ConsensusStatus.SYNTHESIS
        )
        
        # Agregar agente sintetizador si no existe
        synthesizer = None
        for agent in session.agents:
            if agent.role == AgentRole.SYNTHESIZER:
                synthesizer = agent
                break
        
        if not synthesizer and session.agents:
            # Usar el último agente como sintetizador
            synthesizer = session.agents[-1]
        
        if synthesizer:
            # Recopilar todas las posiciones y validaciones
            all_positions_text = ""
            for agent_id, pos in previous_round.positions.items():
                all_positions_text += f"\n\n### {pos.agent.name}\n"
                all_positions_text += f"Posición: {pos.position}\n"
                all_positions_text += f"Puntos: {', '.join(pos.supporting_points[:2])}\n"
                all_positions_text += f"Objeciones recibidas: {len(pos.objections_raised)}\n"
            
            # Agregar validaciones cruzadas
            validations_text = "\n\n## Validaciones Cruzadas:\n"
            for val in previous_round.validations[:10]:  # Limitar para no saturar
                validations_text += f"- {val.evaluator_agent} → {val.evaluated_agent}: {val.agreement_level:.0%} acuerdo"
                if val.identified_fallacies:
                    validations_text += f" (falacias: {', '.join(val.identified_fallacies[:2])})"
                validations_text += "\n"
            
            prompt = f"""# SÍNTESIS DE CONSENSO

## Tema
{session.topic}

## Tu Rol
Sintetizador: {synthesizer.name}
Objetivo: Integrar puntos válidos de todas las posiciones

## Posiciones de los Agentes
{all_positions_text}

{validations_text}

## Tu Tarea
1. **Identificar puntos de convergencia**: ¿Qué argumentos son válidos para todos?
2. **Detectar desacuerdos fundamentales**: ¿Dónde radica la discordancia real?
3. **Proponer síntesis**: Posición integradora que maximize acuerdo
4. **Estimar consenso actual**: ¿Qué % de acuerdo existe?

## Formato de Respuesta
**PUNTOS DE CONVERGENCIA**:
1. [Punto 1 con apoyo amplio]
2. [Punto 2 con apoyo amplio]

**DESEACUERDOS FUNDAMENTALES**:
- [Tema 1]: Posición A vs Posición B
- [Tema 2]: Punto de fricción

**SÍNTESIS PROPUESTA**:
[Posición integradora que reconcilie lo posible]

**CONSENSO ESTIMADO**: [0-100]%

Máximo 400 palabras.
"""
            
            try:
                response_parts = []
                async for token in self._call_agent(synthesizer, prompt):
                    response_parts.append(token)
                
                synthesis_response = "".join(response_parts)
                
                # Parsear síntesis y actualizar consenso
                consensus_estimated = self._extract_consensus_estimate(synthesis_response)
                round_data.global_consensus_score = consensus_estimated
                
                # Generar posiciones refinadas para cada agente
                for agent_id, pos in previous_round.positions.items():
                    refined = await self._generate_refined_position(
                        session, pos, previous_round.validations, synthesis_response
                    )
                    round_data.positions[agent_id] = refined
                
            except Exception as e:
                logger.error("consensus.synthesis_error", error=str(e))
                round_data.positions = previous_round.positions
                round_data.global_consensus_score = previous_round.global_consensus_score
        else:
            round_data.positions = previous_round.positions
            round_data.global_consensus_score = previous_round.global_consensus_score
        
        round_data.validations = previous_round.validations
        round_data.dissent_topics = self._identify_dissent_topics(round_data.validations)
        
        return round_data
    
    def _extract_consensus_estimate(self, response: str) -> float:
        """Extrae el estimado de consenso de la respuesta de síntesis"""
        import re
        match = re.search(r'\*\*CONSENSO ESTIMADO\*\*:\s*(\d+)%', response)
        if match:
            return int(match.group(1)) / 100.0
        
        # Buscar alternativas
        alt_match = re.search(r'(?:consenso|acuerdo).*?(\d+)%', response.lower())
        if alt_match:
            return int(alt_match.group(1)) / 100.0
        
        return 0.5
    
    async def _generate_refined_position(
        self,
        session: ConsensusSession,
        original: AgentPosition,
        validations: List[CrossValidation],
        synthesis: str
    ) -> AgentPosition:
        """Genera posición refinada tras considerar feedback"""
        
        # Encontrar validaciones relevantes para este agente
        relevant_validations = [
            v for v in validations 
            if v.evaluated_agent == original.agent.name
        ]
        
        # Calcular score promedio
        if relevant_validations:
            avg_validation = sum(v.validation_score for v in relevant_validations) / len(relevant_validations)
            original.consensus_score = avg_validation
        
        return original
    
    async def _run_convergence_round(
        self,
        session: ConsensusSession,
        previous_round: ConsensusRoundData,
        round_number: int
    ) -> ConsensusRoundData:
        """
        Rondas 4+: Negociación iterativa para converger.
        """
        round_data = ConsensusRoundData(
            round_number=round_number,
            round_type=ConsensusStatus.CONVERGENCE
        )
        
        # Cada agente responde a objeciones y ajusta posición
        for agent_id, pos in previous_round.positions.items():
            if pos.objections_raised:
                refined = await self._generate_convergence_response(
                    session, pos, round_number
                )
                round_data.positions[agent_id] = refined
            else:
                round_data.positions[agent_id] = pos
        
        # Recalcular consenso
        round_data.global_consensus_score = self._calculate_consensus_score(
            round_data.positions
        )
        
        # Verificar convergencia
        round_data.converged = (
            round_data.global_consensus_score >= self.CONSENSUS_THRESHOLD or
            len(round_data.dissent_topics) == 0
        )
        
        return round_data
    
    async def _generate_convergence_response(
        self,
        session: ConsensusSession,
        position: AgentPosition,
        round_number: int
    ) -> AgentPosition:
        """Genera respuesta de convergencia para un agente"""
        
        prompt = f"""# RONDA DE CONVERGENCIA {round_number}

## Tema
{session.topic}

## Tu Posición Original
{position.position}

## Objeciones Recibidas
{chr(10).join([f"- {obj}" for obj in position.objections_raised[:5]])}

## Tu Tarea
Responde a las objeciones:
1. **¿Cuálas aceptas?** Modifica tu posición incorporando críticas válidas
2. **¿Cuáles rechazas?** Defiende tus argumentos sólidos
3. **Refina tu posición**: Versión mejorada considerando el debate

## Formato
**OBJECIONES ACEPTADAS**:
- [Lista de críticas válidas que incorporas]

**OBJECIONES RECHAZADAS**:
- [Lista con contra-argumentos]

**POSICIÓN REFINADA**:
[Nueva versión mejorada de tu argumento]

**CONFIANZA ACTUALIZADA**: [0-100]%

Máximo 350 palabras.
"""
        
        try:
            response_parts = []
            async for token in self._call_agent(position.agent, prompt):
                response_parts.append(token)
            
            response = "".join(response_parts)
            
            # Actualizar posición
            if "**POSICIÓN REFINADA**:" in response:
                pos_start = response.find("**POSICIÓN REFINADA**:") + 23
                pos_end = response.find("\n\n", pos_start)
                if pos_end == -1:
                    pos_end = len(response)
                new_position = response[pos_start:pos_end].strip()
                if new_position:
                    position.position = new_position
            
            # Limpiar objeciones atendidas
            position.objections_raised = []
            
            return position
            
        except Exception as e:
            logger.error("consensus.convergence_error",
                        agent=position.agent.name,
                        error=str(e))
            return position
    
    def _calculate_consensus_score(
        self,
        positions: Dict[str, AgentPosition],
        validations: Optional[List[CrossValidation]] = None
    ) -> float:
        """
        Calcula el score de consenso grupal.
        
        Método:
        1. Similaridad semántica de posiciones
        2. Niveles de acuerdo en validaciones cruzadas
        3. Confianza de agentes en sus posiciones
        """
        if not positions:
            return 0.0
        
        agent_list = list(positions.values())
        n = len(agent_list)
        
        if n <= 1:
            return 1.0
        
        # Calcular matriz de acuerdo
        agreement_sum = 0.0
        agreement_count = 0
        
        if validations:
            for val in validations:
                agreement_sum += val.agreement_level
                agreement_count += 1
        
        avg_agreement = agreement_sum / agreement_count if agreement_count > 0 else 0.5
        
        # Factor de confianza promedio
        avg_confidence = sum(p.confidence for p in agent_list) / n
        
        # Calcular diversidad de posiciones (usando palabras clave)
        position_keywords = []
        for pos in agent_list:
            # Extraer palabras clave simple
            words = pos.position.lower().split()
            keywords = [w for w in words if len(w) > 4 and w not in ['porque', 'después', 'cuando', 'donde']]
            position_keywords.append(set(keywords[:10]))
        
        # Calcular similaridad de Jaccard promedio
        similarity_sum = 0.0
        similarity_count = 0
        
        for i in range(n):
            for j in range(i + 1, n):
                set_i = position_keywords[i]
                set_j = position_keywords[j]
                
                if set_i or set_j:
                    intersection = len(set_i & set_j)
                    union = len(set_i | set_j)
                    jaccard = intersection / union if union > 0 else 0
                    similarity_sum += jaccard
                    similarity_count += 1
        
        avg_similarity = similarity_sum / similarity_count if similarity_count > 0 else 0.5
        
        # Score ponderado
        consensus_score = (
            avg_agreement * 0.4 +      # Validaciones cruzadas
            avg_similarity * 0.35 +     # Similaridad semántica
            avg_confidence * 0.25       # Confianza de agentes
        )
        
        return min(1.0, max(0.0, consensus_score))
    
    def _identify_dissent_topics(self, validations: List[CrossValidation]) -> List[str]:
        """Identifica temas donde hay disenso significativo"""
        
        # Agrupar por nivel de acuerdo bajo
        low_agreement = [v for v in validations if v.agreement_level < 0.5]
        
        topics = []
        for val in low_agreement:
            if val.identified_fallacies:
                topics.extend(val.identified_fallacies[:2])
        
        # De-duplicar y limitar
        unique_topics = list(set(topics))[:5]
        
        return unique_topics
    
    async def _generate_final_consensus(self, session: ConsensusSession) -> str:
        """Genera el documento de consenso final"""
        
        # Recopilar información de todas las rondas
        final_positions = {}
        if session.rounds:
            final_round = session.rounds[-1]
            final_positions = final_round.positions
        
        # Generar veredicto de consenso
        consensus_doc = f"""# VEREDICTO DE CONSENSO - SYNAPSE COUNCIL v2.0

## Tema
{session.topic}

## Estado del Consenso
- **Score de Consenso**: {session.consensus_score:.1%}
- **Rondas Completadas**: {len(session.rounds)}
- **Estado**: {"Consenso Alcanzado" if session.consensus_score >= self.CONSENSUS_THRESHOLD else "Consenso Parcial"}

## Participantes
"""
        
        for agent_id, pos in final_positions.items():
            consensus_doc += f"- **{pos.agent.name}** ({pos.agent.role.value}): Confianza {pos.confidence:.0%}\\n"
        
        consensus_doc += "\n## Posiciones Finales\n\n"
        
        for agent_id, pos in final_positions.items():
            consensus_doc += f"### {pos.agent.name}\n"
            consensus_doc += f"{pos.position[:300]}...\n\n"
            consensus_doc += f"- **Puntos de apoyo**: {', '.join(pos.supporting_points[:2])}\\n"
            consensus_doc += f"- **Falacias detectadas en su trabajo**: {len(pos.logical_fallacies_detected)}\\n"
            consensus_doc += f"- **Score de consenso**: {pos.consensus_score:.0%}\\n\n"
        
        # Agregar análisis de sesgos si existe
        if session.bias_analysis:
            consensus_doc += "\n## Análisis de Sesgos Detectados\n\n"
            
            for agent_name, biases in session.bias_analysis.get('detected_biases', {}).items():
                if biases:
                    consensus_doc += f"**{agent_name}**:\n"
                    for bias in biases[:3]:
                        consensus_doc += f"- {bias}\\n"
                    consensus_doc += "\n"
        
        consensus_doc += f"""\n---
*Veredicto generado mediante validación cruzada multi-modelo*
*Synapse Council v2.0 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        return consensus_doc
    
    def _analyze_biases(self, session: ConsensusSession) -> Dict[str, Any]:
        """Analiza sesgos detectados en todo el debate"""
        
        bias_analysis = {
            'detected_biases': {},
            'common_fallacies': [],
            'bias_mitigation': []
        }
        
        # Recopilar todas las falacias detectadas
        all_fallacies = []
        
        for round_data in session.rounds:
            for agent_id, pos in round_data.positions.items():
                for fallacy in pos.logical_fallacies_detected:
                    all_fallacies.append({
                        'agent': pos.agent.name,
                        'fallacy': fallacy.get('fallacy', ''),
                        'detected_by': fallacy.get('detected_by', ''),
                        'round': fallacy.get('round', 0)
                    })
        
        # Agrupar por agente
        for fallacy in all_fallacies:
            agent = fallacy['agent']
            if agent not in bias_analysis['detected_biases']:
                bias_analysis['detected_biases'][agent] = []
            bias_analysis['detected_biases'][agent].append(fallacy['fallacy'])
        
        # Falacias comunes
        fallacy_counts = defaultdict(int)
        for f in all_fallacies:
            fallacy_counts[f['fallacy']] += 1
        
        bias_analysis['common_fallacies'] = [
            {'fallacy': k, 'count': v}
            for k, v in sorted(fallacy_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        return bias_analysis
    
    async def _call_agent(
        self,
        agent: DebateAgent,
        prompt: str
    ) -> Any:
        """Llama a un agente (local o cloud)"""
        
        if agent.node == "LOCAL":
            engine_type = EngineType(agent.engine)
            
            async for token in self.local_manager.generate(
                engine_type=engine_type,
                model=agent.model,
                prompt=prompt,
                system=agent.system_prompt,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                stream=True
            ):
                yield token
                
        elif agent.node == "CLOUD" and self.openrouter:
            messages = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            async for token in self.openrouter.chat_completion(
                model=agent.model,
                messages=messages,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
                stream=True
            ):
                yield token
        else:
            raise RuntimeError(f"Agent {agent.name} cannot be called")
    
    async def _persist_consensus_to_db(self, session: ConsensusSession):
        """Persiste el debate de consenso en la base de datos"""
        try:
            async with AsyncSessionLocal() as db_session:
                # Obtener debate
                result = await db_session.execute(
                    select(ConsensusDebate).where(ConsensusDebate.id == session.id)
                )
                db_debate = result.scalar_one_or_none()
                
                if db_debate:
                    db_debate.status = session.status
                    db_debate.consensus_score = session.consensus_score
                    db_debate.final_consensus = session.final_consensus
                    db_debate.transcript_path = session.transcript_path
                    db_debate.completed_at = session.completed_at
                    db_debate.total_tokens_out = session.total_tokens_out
                    db_debate.total_latency_ms = session.total_latency_ms
                    await db_session.commit()
                
                # Guardar rondas
                for round_data in session.rounds:
                    db_round = ConsensusRoundModel(
                        debate_id=session.id,
                        round_number=round_data.round_number,
                        round_type=round_data.round_type.value,
                        global_consensus_score=round_data.global_consensus_score,
                        converged=round_data.converged
                    )
                    db_session.add(db_round)
                
                await db_session.commit()
                
                # Sincronizar con Supabase (cloud)
                logger.info("consensus.syncing_to_supabase", session_id=session.id)
                
                # Preparar datos para sincronización
                debate_data = {
                    'id': session.id,
                    'topic': session.topic,
                    'status': session.status,
                    'total_agents': len(session.agents),
                    'max_rounds': self.MAX_ROUNDS,
                    'consensus_score': session.consensus_score,
                    'final_consensus': session.final_consensus,
                    'bias_analysis': session.bias_analysis,
                    'transcript_path': session.transcript_path,
                    'total_tokens_in': session.total_tokens_in,
                    'total_tokens_out': session.total_tokens_out,
                    'total_latency_ms': session.total_latency_ms,
                    'created_at': session.created_at,
                    'completed_at': session.completed_at,
                    'rounds': [
                        {
                            'round_number': r.round_number,
                            'round_type': r.round_type.value,
                            'global_consensus_score': r.global_consensus_score,
                            'converged': r.converged,
                            'dissent_topics': r.dissent_topics
                        }
                        for r in session.rounds
                    ],
                    'agent_positions': [
                        {
                            'round_number': round_num,
                            'agent_id': agent_pos.agent.id,
                            'agent_name': agent_pos.agent.name,
                            'agent_role': agent_pos.agent.role.value,
                            'position_text': agent_pos.position,
                            'confidence': agent_pos.confidence,
                            'consensus_score': agent_pos.consensus_score,
                            'supporting_points': agent_pos.supporting_points,
                            'objections_raised': agent_pos.objections_raised,
                            'logical_fallacies': [f.get('fallacy', '') for f in agent_pos.logical_fallacies_detected]
                        }
                        for round_num, round_data in enumerate(session.rounds, 1)
                        for agent_pos in round_data.positions.values()
                    ]
                }
                
                sync_result = await self.supabase_sync.sync_consensus_debate(debate_data)
                
                if sync_result.get('synced'):
                    logger.info("consensus.supabase_sync_success",
                               session_id=session.id,
                               rounds_synced=sync_result.get('rounds_synced'),
                               positions_synced=sync_result.get('positions_synced'))
                else:
                    logger.warning("consensus.supabase_sync_failed",
                                  session_id=session.id,
                                  error=sync_result.get('error', 'unknown'))
                
        except Exception as e:
            logger.error("consensus.db_persist_error", error=str(e))
    
    async def _save_consensus_transcript(self, session: ConsensusSession) -> str:
        """Guarda la transcripción del debate de consenso"""
        
        filename = f"consensus_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(TRANSCRIPTS_DIR, filename)
        
        content = f"""# TRANSCRIPCIÓN DE DEBATE DE CONSENSO

## {session.topic}

**Session ID**: `{session.id}`
**Estado**: {session.status}
**Consenso**: {session.consensus_score:.1%}
**Rondas**: {len(session.rounds)}
**Iniciado**: {session.created_at}
**Completado**: {session.completed_at}

---

## Resumen por Rondas

"""
        
        for round_data in session.rounds:
            content += f"### Ronda {round_data.round_number}: {round_data.round_type.value.upper()}\n\n"
            content += f"**Score de Consenso**: {round_data.global_consensus_score:.1%}\n"
            
            if round_data.dissent_topics:
                content += f"**Temas de Disenso**: {', '.join(round_data.dissent_topics)}\n"
            
            content += "\n**Posiciones**:\n\n"
            for agent_id, pos in round_data.positions.items():
                content += f"- **{pos.agent.name}**: {pos.position[:200]}...\n"
                content += f"  - Confianza: {pos.confidence:.0%} | Consenso: {pos.consensus_score:.0%}\n"
            
            if round_data.validations:
                content += "\n**Validaciones Cruzadas**:\n\n"
                for val in round_data.validations[:5]:
                    content += f"- {val.evaluator_agent} → {val.evaluated_agent}: {val.agreement_level:.0%} acuerdo\n"
            
            content += "\n---\n\n"
        
        content += f"\n## {session.final_consensus}\n"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def get_session(self, session_id: str) -> Optional[ConsensusSession]:
        """Obtiene una sesión de consenso activa"""
        return self.active_sessions.get(session_id)


# Configuración predefinida para debates de consenso
def get_consensus_debate_config(topic: str) -> List[DebateAgent]:
    """
    Configuración para debate de consenso con 4 agentes diversos.
    """
    return [
        # Posición A - Enfoque filosófico
        DebateAgent(
            id="philosopher_llama3",
            name="Filósofo Racional",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3:8b",
            provider="meta",
            system_prompt="Eres un filósofo racional. Argumenta desde principios lógicos y éticos fundamentales. "
                        "Busca la validez deductiva y la consistencia interna. Sé riguroso.",
            temperature=0.7,
            max_tokens=600
        ),
        
        # Posición B - Enfoque pragmático
        DebateAgent(
            id="pragmatist_mistral",
            name="Pragmatista Crítico",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="mistral:7b",
            provider="mistral",
            system_prompt="Eres un pragmatista crítico. Examina las consecuencias prácticas y empíricas. "
                        "Cuestiona supuestos no verificados. Sé constructivo pero exigente.",
            temperature=0.8,
            max_tokens=600
        ),
        
        # Posición C - Enfoque sistémico
        DebateAgent(
            id="systemic_qwen",
            name="Analista Sistémico",
            role=AgentRole.SYNTHESIZER,
            node="LOCAL",
            engine="ollama",
            model="qwen2.5:3b",
            provider="alibaba",
            system_prompt="Eres un analista sistémico. Busca patrones, interconexiones y efectos en cadena. "
                        "Intenta integrar perspectivas en marcos coherentes.",
            temperature=0.7,
            max_tokens=600
        ),
        
        # Posición D - Enfoque escéptico/riguroso
        DebateAgent(
            id="skeptic_deepseek",
            name="Escéptico Metodológico",
            role=AgentRole.REFINER,
            node="LOCAL",
            engine="ollama",
            model="deepseek-r1:7b",
            provider="deepseek",
            system_prompt="Eres un escéptico metodológico. Detecta falacias, sesgos y razonamientos inválidos. "
                        "Demanda evidencia. Sé el guardián de la rigurosidad lógica.",
            temperature=0.6,
            max_tokens=700
        ),
    ]
