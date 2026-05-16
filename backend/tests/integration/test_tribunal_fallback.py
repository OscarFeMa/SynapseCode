"""
Integration tests for tribunal fallback chains
"""
import asyncio
from backend.engine.agent_orchestrator import AgentResult
from backend.engine.tribunal import TribunalCouncil
from backend.engine.tribunal_config import build_tribunal_config
from backend.config import get_settings


class TestTribunalFallback:
    """Pruebas de las fallback chains del Tribunal"""

    def test_tribunal_uses_fallback_when_primary_magistrate_fails(self):
        class FakeOrchestrator:
            def __init__(self):
                self.calls = []

            async def call_agent(self, **kwargs):
                config = kwargs["config"]
                self.calls.append(config.model)
                if len(self.calls) == 1:
                    return AgentResult(
                        call_id="failed-primary",
                        slot=config.slot,
                        node=config.node,
                        status="FAILED",
                        error_message="model unavailable",
                    )
                return AgentResult(
                    call_id="fallback-ok",
                    slot=config.slot,
                    node=config.node,
                    status="COMPLETED",
                    response="Fallback completo. Score: 88/100",
                )

        async def scenario():
            tribunal = TribunalCouncil()
            tribunal.orchestrator = FakeOrchestrator()
            events = []

            result = await tribunal._call_magistrate_with_fallback(
                role="evidence",
                session_id="tribunal-fallback",
                round_id="round-1",
                round_number=1,
                phase="TRIBUNAL",
                prompt="Evalua evidencias",
                db_session=None,
                on_event=lambda event, payload: events.append((event, payload)),
            )

            assert result.status == "COMPLETED"
            assert result.call_id == "fallback-ok"
            assert len(tribunal.orchestrator.calls) == 2
            assert any(event == "tribunal_fallback" for event, _ in events)

        asyncio.run(scenario())
