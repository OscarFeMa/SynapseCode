"""
Integration tests for reputation manager
"""

import asyncio

from backend.engine.reputation_unified import ReputationManager, reputation_service


class TestReputationManager:
    """Pruebas del gestor de reputacion EMA"""

    def test_reputation_imports(self):
        assert ReputationManager is not None
        assert reputation_service is not None

    def test_reputation_service_instance(self):
        assert hasattr(reputation_service, "get_reputation")
        assert hasattr(reputation_service, "list_all")
        assert hasattr(reputation_service, "update_after_turn")
        assert hasattr(reputation_service, "update_after_session")

    def test_reputation_update_and_get(self):
        async def scenario():
            model = "test-model-rep"
            role = "analyst"
            await reputation_service.update_after_turn(
                model=model,
                provider="test",
                role=role,
                tokens_out=100,
                latency_ms=500,
                success=True,
                intervention_type="analysis",
            )
            rep = await reputation_service.get_reputation(model, role)
            assert rep is not None

        asyncio.run(scenario())

    def test_reputation_list_all(self):
        async def scenario():
            reps = await reputation_service.list_all(min_turns=0)
            assert isinstance(reps, list)

        asyncio.run(scenario())
