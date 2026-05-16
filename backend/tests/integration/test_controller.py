"""
Integration tests for controller methods
"""
import asyncio
from unittest.mock import AsyncMock
from backend.engine.sequential_debate_controller import SequentialDebateController
from backend.engine.debate_models import DebateAgent, AgentRole


class TestSequentialDebateController:
    """Pruebas del controlador de debates secuenciales"""

    def test_controller_schedules_preload_for_next_local_ollama_model(self):
        controller = SequentialDebateController()
        agents = [
            DebateAgent(
                id="a1", name="Agent 1", role=AgentRole.ANALYST, node="LOCAL",
                engine="ollama", model="llama3.2:latest", provider="meta", system_prompt="",
            ),
            DebateAgent(
                id="a2", name="Agent 2", role=AgentRole.CRITIC, node="LOCAL",
                engine="ollama", model="mistral:latest", provider="mistral", system_prompt="",
            ),
            DebateAgent(
                id="a3", name="Agent 3", role=AgentRole.SYNTHESIZER, node="CLOUD",
                engine="openrouter", model="openai/gpt-4o-mini", provider="openai", system_prompt="",
            ),
        ]
        assert controller._find_next_preload_model(agents, current_index=0) == "mistral:latest"
        assert controller._find_next_preload_model(agents, current_index=1) is None

    def test_controller_has_reductio_engine(self):
        controller = SequentialDebateController()
        assert hasattr(controller, "reductio_engine")
        assert controller.reductio_engine is not None

    def test_local_agent_uses_deterministic_response_cache(self):
        from sqlalchemy import delete
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import PromptResponseCache

        agent = DebateAgent(
            id="cache-agent", name="Cache Agent", role=AgentRole.ANALYST, node="LOCAL",
            engine="ollama", model="llama3.2:latest", provider="meta",
            system_prompt="", temperature=0.3, max_tokens=128,
        )

        async def scenario():
            await init_db()
            controller = SequentialDebateController()
            call_counter = {"count": 0}

            async def fake_generate(**kwargs):
                call_counter["count"] += 1
                for token in ["Hola", " mundo"]:
                    yield token

            controller.local_manager.generate = fake_generate
            prompt = "Explica por que la cache reduce latencia."

            first = await controller._run_local_agent(agent, prompt)
            second = await controller._run_local_agent(agent, prompt)

            assert first["text"] == "Hola mundo"
            assert second["text"] == "Hola mundo"
            assert second["cache_hit"] is True
            assert call_counter["count"] == 1

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(PromptResponseCache).where(PromptResponseCache.model == agent.model)
                )
                await db_session.commit()

        asyncio.run(scenario())

    def test_reductio_proof_is_persisted_with_scan_metadata(self):
        import uuid
        from sqlalchemy import select, delete
        from backend.database.local_db import init_db, AsyncSessionLocal
        from backend.database.models import SequentialDebate, ReductioAbsurdumProof
        from backend.engine.reductio_absurdum import AbsurdumProof as RuntimeAbsurdumProof, ComplacencyScan

        debate_id = f"reductio-{uuid.uuid4()}"

        async def scenario():
            await init_db()
            async with AsyncSessionLocal() as db_session:
                db_session.add(
                    SequentialDebate(
                        id=debate_id, topic="Debate de prueba reductio",
                        status="completed", total_turns=2,
                    )
                )
                await db_session.commit()

            controller = SequentialDebateController()
            scan = ComplacencyScan(
                consensus_areas=["La automatizacion siempre mejora la calidad"],
                weak_assumptions=["La automatizacion siempre mejora la calidad"],
                unquestioned_premises=["Siempre implica menos errores"],
                overall_complacency_risk=0.82,
                recommendations=["Desafiar absolutos en automatizacion"],
            )
            proof = RuntimeAbsurdumProof(
                proposition="La automatizacion siempre mejora la calidad",
                extreme_case="Si se automatiza toda decision sin revision humana, aparecen errores sistemicos.",
                contradiction="Esto contradice la necesidad de supervisar excepciones complejas.",
                is_valid=False, confidence_score=0.8,
                questioning_agent="Critic", challenged_agent="Analyst",
            )

            await controller._persist_reductio_absurdum_proof(
                debate_id=debate_id, iteration_number=2,
                complacency_scan=scan, proof=proof,
            )

            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(ReductioAbsurdumProof).where(ReductioAbsurdumProof.debate_id == debate_id)
                )
                record = result.scalar_one()

            assert record.iteration_number == 2
            assert record.proposition == proof.proposition
            assert record.questioning_agent == "Critic"
            assert record.challenged_agent == "Analyst"
            assert record.overall_complacency_risk == 0.82
            assert record.weak_assumptions == ["La automatizacion siempre mejora la calidad"]
            assert record.recommendations == ["Desafiar absolutos en automatizacion"]
            assert record.is_valid is False

            async with AsyncSessionLocal() as db_session:
                await db_session.execute(
                    delete(ReductioAbsurdumProof).where(ReductioAbsurdumProof.debate_id == debate_id)
                )
                await db_session.execute(
                    delete(SequentialDebate).where(SequentialDebate.id == debate_id)
                )
                await db_session.commit()

        asyncio.run(scenario())
