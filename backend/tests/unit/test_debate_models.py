"""
Unit tests for debate models (data structures)
"""

from datetime import datetime

from backend.engine.debate_models import (
    AgentRole,
    CruzamientoCritico,
    DebateAgent,
    DebateSession,
    DebateTurn,
    IteracionDebate,
)


class TestDebateModels:
    """Pruebas de los modelos de datos del debate"""

    def test_agent_role_enum(self):
        roles = [r.value for r in AgentRole]
        assert "analyst" in roles
        assert "critic" in roles
        assert "synthesizer" in roles
        assert "refiner" in roles
        assert "moderator" in roles
        assert "validator" in roles
        assert "consensus" in roles
        assert "tribunal" in roles

    def test_debate_agent_creation(self):
        agent = DebateAgent(
            id="test-agent",
            name="Test Agent",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="Test prompt",
            temperature=0.7,
            max_tokens=500,
        )
        assert agent.id == "test-agent"
        assert agent.role == AgentRole.ANALYST
        assert agent.temperature == 0.7

    def test_debate_turn_creation(self):
        agent = DebateAgent(
            id="a1",
            name="A1",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="",
            temperature=0.7,
            max_tokens=500,
        )
        turn = DebateTurn(turn_number=1, agent=agent, prompt_sent="Test prompt")
        assert turn.turn_number == 1
        assert turn.status == "pending"
        assert turn.tokens_in == 0

    def test_debate_session_creation(self):
        session = DebateSession(id="test-session", topic="Test topic", status="created")
        assert session.id == "test-session"
        assert session.topic == "Test topic"
        assert session.status == "created"
        assert session.max_iterations == 3

    def test_cruzamiento_critico(self):
        cruz = CruzamientoCritico(
            from_agent="Agent A",
            to_agent="Agent B",
            target_argument="Test argument",
            response="Test response",
            iteration=1,
        )
        assert cruz.from_agent == "Agent A"
        assert cruz.to_agent == "Agent B"
        assert cruz.iteration == 1

    def test_iteracion_debate(self):
        iteration = IteracionDebate(iteration_number=1, phase="analysis")
        assert iteration.iteration_number == 1
        assert iteration.phase == "analysis"
        assert len(iteration.turns) == 0
        assert len(iteration.cruzamientos) == 0

    def test_session_build_context_prompt(self):
        session = DebateSession(id="s1", topic="Test topic", status="completed")
        agent = DebateAgent(
            id="a1",
            name="A1",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2:latest",
            provider="meta",
            system_prompt="",
            temperature=0.7,
            max_tokens=500,
        )
        turn = DebateTurn(
            turn_number=1,
            agent=agent,
            prompt_sent="p",
            response_received="This is a comprehensive analysis of the topic with detailed evidence and structured arguments supporting the main position.",
            status="completed",
        )
        session.turns.append(turn)
        context = session.build_context_prompt(agent)
        assert "Test topic" in context
        assert "A1" in context

    def test_debate_session_has_pause_fields(self):
        session = DebateSession(id="test", topic="test", status="paused")
        assert hasattr(session, "paused_at")
        assert hasattr(session, "pause_reason")
        session.paused_at = datetime.now()
        session.pause_reason = "test reason"
        assert session.pause_reason == "test reason"

    def test_sliding_window_disabled_returns_full_context(self):
        session = DebateSession(id="s1", topic="Test", enable_sliding_window=False)
        for i in range(5):
            agent = DebateAgent(
                id=f"a{i}",
                name=f"Agent {i}",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="llama3.2",
                provider="meta",
                system_prompt="",
            )
            iteration = IteracionDebate(iteration_number=i + 1, phase="analysis")
            turn = DebateTurn(
                turn_number=i + 1,
                agent=agent,
                prompt_sent="p",
                response_received=f"Response {i} with detailed analysis and arguments about the topic.",
                status="completed",
            )
            iteration.turns.append(turn)
            session.iterations.append(iteration)

        context = session.get_iteration_context(5)
        assert "ITERACION 1" in context
        assert "ITERACION 5" in context
        assert "RESUMEN" not in context

    def test_sliding_window_compresses_old_iterations(self):
        session = DebateSession(id="s1", topic="Test", enable_sliding_window=True)
        for i in range(6):
            agent = DebateAgent(
                id=f"a{i}",
                name=f"Agent {i}",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="llama3.2",
                provider="meta",
                system_prompt="",
            )
            iteration = IteracionDebate(iteration_number=i + 1, phase="analysis")
            turn = DebateTurn(
                turn_number=i + 1,
                agent=agent,
                prompt_sent="p",
                response_received=f"Response {i} with detailed analysis and arguments about the topic.",
                status="completed",
            )
            iteration.turns.append(turn)
            session.iterations.append(iteration)

        context = session.get_iteration_context(6)
        assert "RESUMEN DE 4 ITERACIONES ANTERIORES" in context
        assert "ITERACIONES RECIENTES (detalle completo)" in context
        assert "Iter 1" in context
        assert "ITERACION 5" in context
        assert "ITERACION 6" in context  # Iteration 6 is the most recent detailed one

    def test_sliding_window_preserves_consensus_points(self):
        session = DebateSession(id="s1", topic="Test", enable_sliding_window=True)
        for i in range(5):
            agent = DebateAgent(
                id=f"a{i}",
                name=f"Agent {i}",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="llama3.2",
                provider="meta",
                system_prompt="",
            )
            iteration = IteracionDebate(iteration_number=i + 1, phase="analysis")
            iteration.consensus_points.append(f"Consensus point {i}")
            iteration.disagreement_points.append(f"Disagreement point {i}")
            turn = DebateTurn(
                turn_number=i + 1,
                agent=agent,
                prompt_sent="p",
                response_received=f"Response {i}",
                status="completed",
            )
            iteration.turns.append(turn)
            session.iterations.append(iteration)

        context = session.get_iteration_context(5)
        assert "Puntos de consenso alcanzados" in context
        assert "Consensus point 0" in context
        assert "Puntos de desacuerdo pendientes" in context
        assert "Disagreement point 0" in context

    def test_iteration_compact_summary(self):
        agent = DebateAgent(
            id="a1",
            name="Agent 1",
            role=AgentRole.ANALYST,
            node="LOCAL",
            engine="ollama",
            model="llama3.2",
            provider="meta",
            system_prompt="",
        )
        iteration = IteracionDebate(iteration_number=1, phase="analysis")
        iteration.turns.append(
            DebateTurn(
                turn_number=1,
                agent=agent,
                prompt_sent="p",
                response_received="First sentence. Second sentence. Third sentence. Fourth sentence.",
                status="completed",
            )
        )
        summary = iteration.get_compact_summary()
        assert "Agent 1 (analyst)" in summary
        assert len(summary) <= 500

    def test_sliding_window_small_context_uses_full(self):
        session = DebateSession(id="s1", topic="Test", enable_sliding_window=True)
        for i in range(2):
            agent = DebateAgent(
                id=f"a{i}",
                name=f"Agent {i}",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="llama3.2",
                provider="meta",
                system_prompt="",
            )
            iteration = IteracionDebate(iteration_number=i + 1, phase="analysis")
            turn = DebateTurn(
                turn_number=i + 1,
                agent=agent,
                prompt_sent="p",
                response_received=f"Response {i}",
                status="completed",
            )
            iteration.turns.append(turn)
            session.iterations.append(iteration)

        context = session.get_iteration_context(2)
        assert "RESUMEN" not in context
        assert "ITERACION 1" in context

    def test_build_context_prompt_sliding_window_on_turns(self):
        session = DebateSession(id="s1", topic="Test", enable_sliding_window=True)
        for i in range(15):
            agent = DebateAgent(
                id=f"a{i}",
                name=f"Agent {i}",
                role=AgentRole.ANALYST,
                node="LOCAL",
                engine="ollama",
                model="llama3.2",
                provider="meta",
                system_prompt="",
            )
            # Usar respuestas largas para pasar el quality filter
            response_text = (
                f"Análisis detallado del tema desde la perspectiva del agente {i}. "
                f"Posición: argumento principal con evidencia sólida. "
                f"Argumento: desarrollo extenso con múltiples puntos de vista. "
                f"Evidencia: datos y referencias que respaldan la posición adoptada en este turno."
            )
            turn = DebateTurn(
                turn_number=i + 1,
                agent=agent,
                prompt_sent="p",
                response_received=response_text,
                status="completed",
            )
            session.turns.append(turn)

        current_agent = DebateAgent(
            id="current",
            name="Current",
            role=AgentRole.CRITIC,
            node="LOCAL",
            engine="ollama",
            model="llama3.2",
            provider="meta",
            system_prompt="",
        )
        context = session.build_context_prompt(current_agent)
        assert "Resumen de 5 turnos anteriores" in context
        assert "Turnos recientes (detalle completo)" in context
        assert "Turno 15" in context
        # Turno 10 should be in summary section, not in detailed recent turns
        assert "Turno 10" in context  # Appears in summary
        # Verify the sliding window structure: old turns summarized, recent detailed
        assert context.index("Resumen de 5 turnos anteriores") < context.index("Turnos recientes")
