"""
Unit tests for convergence evaluator
"""
from backend.engine.convergence import ConvergenceEvaluator


class TestConvergenceEvaluator:
    """Pruebas del evaluador de convergencia"""

    def test_convergence_imports(self):
        assert ConvergenceEvaluator is not None

    def test_convergence_evaluate(self):
        evaluator = ConvergenceEvaluator()
        result = evaluator.evaluate(
            local_synthesis="Test synthesis about AI benefits",
            cloud_synthesis="AI is beneficial for society",
            round_number=2,
            max_rounds=3
        )
        assert hasattr(result, "similarity_score")
        assert hasattr(result, "should_stop")
        assert hasattr(result, "consensus_level")

    def test_convergence_early_stop(self):
        evaluator = ConvergenceEvaluator()
        result = evaluator.evaluate(
            local_synthesis="The sky is blue and clear",
            cloud_synthesis="The sky is blue and clear",
            round_number=3,
            max_rounds=3
        )
        assert result.similarity_score > 0.5
