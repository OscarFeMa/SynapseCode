"""
Unit tests for intervention taxonomy
"""

from backend.engine.intervention_taxonomy import detect_intervention_type


class TestInterventionTaxonomy:
    """Pruebas de la clasificacion de actos discursivos"""

    def test_intervention_taxonomy_imports(self):
        assert callable(detect_intervention_type)

    def test_detect_analysis_intervention(self):
        result = detect_intervention_type(
            "El analisis muestra que la IA tiene beneficios significativos...",
            "analyst",
        )
        assert isinstance(result, str)

    def test_detect_criticism_intervention(self):
        result = detect_intervention_type(
            "Sin embargo, hay debilidades en el argumento presentado...", "critic"
        )
        assert isinstance(result, str)

    def test_detect_synthesis_intervention(self):
        result = detect_intervention_type(
            "En sintesis, los puntos de acuerdo son...", "synthesizer"
        )
        assert isinstance(result, str)
