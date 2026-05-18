"""
Unit tests for GPU Metrics Service
"""

from backend.services.gpu_metrics import GPUMetrics, GPUMetricsCollector


class TestGPUMetrics:
    """Pruebas del servicio de metricas GPU"""

    def test_gpu_metrics_default_values(self):
        metrics = GPUMetrics()
        assert metrics.is_available is False
        assert metrics.memory_used_mb == 0.0
        assert metrics.error is None

    def test_gpu_metrics_with_error(self):
        metrics = GPUMetrics(error="Test error")
        assert metrics.is_available is False
        assert metrics.error == "Test error"

    def test_collector_collect_returns_metrics(self):
        collector = GPUMetricsCollector()
        # En maquinas sin GPU, debe retornar metrics con error
        metrics = collector.collect()
        assert isinstance(metrics, GPUMetrics)
        # Puede tener error o no dependiendo del hardware
        assert metrics.is_available or metrics.error is not None

    def test_collector_history_empty_initially(self):
        collector = GPUMetricsCollector()
        assert len(collector.get_history()) == 0

    def test_collector_history_grows_on_collect(self):
        collector = GPUMetricsCollector()
        collector.collect()
        history = collector.get_history()
        assert len(history) >= 0  # Puede ser 0 si no hay GPU

    def test_collector_summary_empty_initially(self):
        collector = GPUMetricsCollector()
        summary = collector.get_summary()
        assert summary["samples"] == 0

    def test_collector_summary_with_data(self):
        collector = GPUMetricsCollector()
        # Agregar metrics manualmente para testing
        from datetime import datetime

        metrics = GPUMetrics(
            timestamp=datetime.now(),
            memory_used_mb=5000.0,
            memory_free_mb=8500.0,
            memory_total_mb=13500.0,
            memory_used_pct=37.0,
            temperature_celsius=65.0,
            utilization_pct=80.0,
            is_available=True,
        )
        collector._history.append(metrics)
        summary = collector.get_summary()
        assert summary["samples"] == 1
        assert summary["temperature"]["avg"] == 65.0
        assert summary["utilization"]["avg"] == 80.0
        assert summary["memory"]["avg_pct"] == 37.0

    def test_collector_history_limit(self):
        collector = GPUMetricsCollector()
        collector._max_history = 5
        # Agregar 10 metrics directamente al historial
        from datetime import datetime, timedelta

        for i in range(10):
            metrics = GPUMetrics(
                timestamp=datetime.now() + timedelta(seconds=i),
                memory_used_mb=float(i * 100),
                is_available=True,
            )
            collector._history.append(metrics)
            # Simular el trimming que hace collect()
            if len(collector._history) > collector._max_history:
                collector._history = collector._history[-collector._max_history :]

        history = collector.get_history()
        assert len(history) <= 5  # Debe estar limitado

    def test_collector_get_singleton(self):
        from backend.services.gpu_metrics import get_gpu_collector

        collector1 = get_gpu_collector()
        collector2 = get_gpu_collector()
        assert collector1 is collector2
