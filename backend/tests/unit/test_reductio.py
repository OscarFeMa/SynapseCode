"""
Unit tests for reductio absurdum engine
"""

from backend.engine.reductio_absurdum import (
    AbsurdumProof,
    ComplacencyScan,
    ReductioAbsurdumEngine,
    get_reductio_absurdum_engine,
)


class TestReductioAbsurdum:
    """Pruebas del motor de Reduccion al Absurdo"""

    def test_reductio_module_imports(self):
        assert ReductioAbsurdumEngine is not None
        assert AbsurdumProof is not None
        assert ComplacencyScan is not None

    def test_reductio_engine_extract_propositions(self):
        engine = get_reductio_absurdum_engine()
        text = "La IA es beneficiosa porque automatiza tareas repetitivas y mejora la productividad."
        propositions = engine.extract_propositions_from_text(text)
        assert isinstance(propositions, list)
        assert len(propositions) > 0

    def test_reductio_complacency_scan(self):
        engine = get_reductio_absurdum_engine()
        scan = engine.analyze_consensus_points(
            consensus_points=["La IA es buena", "La tecnologia avanza"],
            dissent_points=[],
            debate_history="Debate sobre IA",
            iteration_number=1,
        )
        assert hasattr(scan, "overall_complacency_risk")
        assert hasattr(scan, "weak_assumptions")
        assert hasattr(scan, "recommendations")
