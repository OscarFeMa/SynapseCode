"""
Unit tests for quality monitor
"""

from backend.engine.quality_monitor import (
    QualityMonitor,
    evaluate_response,
    is_response_usable,
)


class TestQualityMonitor:
    """Pruebas del monitor de calidad"""

    def test_quality_monitor_imports(self):
        assert QualityMonitor is not None
        assert callable(is_response_usable)
        assert callable(evaluate_response)

    def test_is_response_usable_good_response(self):
        long_response = "El analisis muestra que la inteligencia artificial tiene beneficios significativos en multiples areas. La automatizacion de tareas repetitivas permite a los humanos enfocarse en trabajo creativo y estrategico. Ademas, los sistemas de IA pueden procesar grandes volumenes de datos en tiempo real, identificando patrones que serian imposibles de detectar manualmente. La evidencia acumulada sugiere que la adopcion responsable de estas tecnologias puede transformar positivamente la sociedad."
        assert is_response_usable(long_response, "analyst") is True

    def test_is_response_usable_empty_response(self):
        assert is_response_usable("", "analyst") is False
        assert is_response_usable("   ", "analyst") is False

    def test_is_response_usable_error_response(self):
        assert is_response_usable("[ERROR: Connection failed]", "analyst") is False

    def test_evaluate_response_returns_score(self):
        score, details = evaluate_response("Good response with detailed analysis.", "analyst")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
