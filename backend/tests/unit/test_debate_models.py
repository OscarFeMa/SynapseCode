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
