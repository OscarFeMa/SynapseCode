"""
Integration tests for Prometheus metrics
"""

from backend.monitoring.prometheus import (
    record_debate_completed,
    record_debate_report_cache_hit,
    record_prompt_cache_hit,
    render_prometheus_metrics,
)


class TestPrometheusMetrics:
    """Pruebas del sistema de metricas Prometheus"""

    def test_prometheus_module_imports(self):
        assert callable(record_debate_completed)
        assert callable(record_debate_report_cache_hit)

    def test_prometheus_metrics_render(self):
        metrics = render_prometheus_metrics()
        assert "debate_duration_seconds" in metrics or "debate_tokens_generated" in metrics

    def test_prometheus_debate_completed_recording(self):
        try:
            record_debate_completed(total_tokens_out=500, total_latency_ms=3000, mode="standard")
        except Exception as e:
            assert False, f"record_debate_completed raised: {e}"

    def test_prometheus_cache_hit_recording(self):
        try:
            record_prompt_cache_hit("deterministic")
        except Exception as e:
            assert False, f"record_prompt_cache_hit raised: {e}"

    def test_prometheus_report_cache_hit_recording(self):
        try:
            record_debate_report_cache_hit("memory")
        except Exception as e:
            assert False, f"record_debate_report_cache_hit raised: {e}"
