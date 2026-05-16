"""
Prometheus-style in-process metrics for Synapse Council.
"""
from __future__ import annotations

from threading import Lock
from typing import Dict, Tuple, Optional


HTTP_DURATION_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


def _labels_key(labels: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted((key, str(value)) for key, value in labels.items()))


def _format_labels(labels: Tuple[Tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    rendered = ",".join(f'{key}="{value}"' for key, value in labels)
    return f"{{{rendered}}}"


class PrometheusMetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = {}
        self._gauges: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = {}
        self._histograms: Dict[str, Dict[str, object]] = {}

    def inc_counter(self, name: str, amount: float = 1.0, **labels: str) -> None:
        with self._lock:
            series = self._counters.setdefault(name, {})
            key = _labels_key(labels)
            series[key] = series.get(key, 0.0) + amount

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            series = self._gauges.setdefault(name, {})
            series[_labels_key(labels)] = value

    def observe_histogram(
        self,
        name: str,
        value: float,
        buckets=HTTP_DURATION_BUCKETS,
        **labels: str,
    ) -> None:
        with self._lock:
            histogram = self._histograms.setdefault(
                name,
                {
                    "buckets": tuple(buckets),
                    "series": {},
                },
            )
            key = _labels_key(labels)
            series = histogram["series"].setdefault(
                key,
                {
                    "bucket_counts": {bucket: 0.0 for bucket in histogram["buckets"]},
                    "count": 0.0,
                    "sum": 0.0,
                },
            )
            for bucket in histogram["buckets"]:
                if value <= bucket:
                    series["bucket_counts"][bucket] += 1.0
            series["count"] += 1.0
            series["sum"] += value

    def render(self) -> str:
        lines = []
        with self._lock:
            for name, series in sorted(self._counters.items()):
                lines.append(f"# TYPE {name} counter")
                for labels, value in sorted(series.items()):
                    lines.append(f"{name}{_format_labels(labels)} {value}")

            for name, series in sorted(self._gauges.items()):
                lines.append(f"# TYPE {name} gauge")
                for labels, value in sorted(series.items()):
                    lines.append(f"{name}{_format_labels(labels)} {value}")

            for name, histogram in sorted(self._histograms.items()):
                lines.append(f"# TYPE {name} histogram")
                for labels, values in sorted(histogram["series"].items()):
                    cumulative = 0.0
                    for bucket in histogram["buckets"]:
                        cumulative = values["bucket_counts"][bucket]
                        bucket_labels = dict(labels)
                        bucket_labels["le"] = str(bucket)
                        lines.append(f'{name}_bucket{_format_labels(_labels_key(bucket_labels))} {cumulative}')
                    inf_labels = dict(labels)
                    inf_labels["le"] = "+Inf"
                    lines.append(f'{name}_bucket{_format_labels(_labels_key(inf_labels))} {values["count"]}')
                    lines.append(f"{name}_count{_format_labels(labels)} {values['count']}")
                    lines.append(f"{name}_sum{_format_labels(labels)} {values['sum']}")

        return "\n".join(lines) + "\n"


registry = PrometheusMetricsRegistry()


def observe_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    registry.inc_counter(
        "synapse_http_requests_total",
        method=method,
        path=path,
        status_code=str(status_code),
    )
    registry.observe_histogram(
        "synapse_http_request_duration_seconds",
        duration_seconds,
        method=method,
        path=path,
    )


def record_debate_report_generated(source: str) -> None:
    registry.inc_counter("synapse_debate_reports_generated_total", source=source)


def record_debate_report_cache_hit(source: str) -> None:
    registry.inc_counter("synapse_debate_report_cache_hits_total", source=source)


def record_prompt_cache_hit(cache_type: str) -> None:
    registry.inc_counter("synapse_prompt_cache_hits_total", cache_type=cache_type)


def record_prompt_cache_miss(cache_type: str) -> None:
    registry.inc_counter("synapse_prompt_cache_misses_total", cache_type=cache_type)


def record_debate_completed(total_tokens_out: int, total_latency_ms: int, mode: Optional[str] = None) -> None:
    labels = {"mode": mode or "unknown"}
    registry.inc_counter("synapse_debates_completed_total", **labels)
    registry.inc_counter("synapse_debate_tokens_generated_total", amount=float(total_tokens_out), **labels)
    registry.observe_histogram(
        "synapse_debate_duration_seconds",
        max(total_latency_ms, 0) / 1000.0,
        **labels,
    )


def record_warehouse_debate_aggregated(debate_type: str, status: str) -> None:
    registry.inc_counter(
        "synapse_warehouse_debates_aggregated_total",
        debate_type=debate_type,
        status=status,
    )


def record_supabase_sync_failure(reason: str = "unknown") -> None:
    registry.inc_counter("synapse_supabase_sync_failures_total", reason=reason)


def record_supabase_sync_retry(reason: str = "unknown") -> None:
    registry.inc_counter("synapse_supabase_sync_retries_total", reason=reason)


def set_supabase_sync_queue_size(size: int) -> None:
    registry.set_gauge("synapse_supabase_sync_queue_size", float(size))


def render_prometheus_metrics() -> str:
    return registry.render()


# Bootstrap de series base para que Prometheus vea métricas estables aunque aún no haya tráfico de negocio.
registry.inc_counter("synapse_debate_reports_generated_total", amount=0.0, source="database_backfill")
registry.inc_counter("synapse_debate_report_cache_hits_total", amount=0.0, source="memory")
registry.inc_counter("synapse_debate_report_cache_hits_total", amount=0.0, source="database")
registry.inc_counter("synapse_prompt_cache_hits_total", amount=0.0, cache_type="deterministic")
registry.inc_counter("synapse_prompt_cache_misses_total", amount=0.0, cache_type="deterministic")
registry.inc_counter("synapse_prompt_cache_hits_total", amount=0.0, cache_type="semantic")
registry.inc_counter("synapse_prompt_cache_misses_total", amount=0.0, cache_type="semantic")
registry.inc_counter("synapse_debates_completed_total", amount=0.0, mode="standard")
registry.inc_counter("synapse_debate_tokens_generated_total", amount=0.0, mode="standard")
registry.observe_histogram("synapse_debate_duration_seconds", 0.0, mode="standard")
registry.set_gauge("synapse_supabase_sync_queue_size", 0.0)
registry.inc_counter("synapse_supabase_sync_failures_total", amount=0.0, reason="unknown")
registry.inc_counter("synapse_supabase_sync_retries_total", amount=0.0, reason="unknown")
registry.inc_counter(
    "synapse_warehouse_debates_aggregated_total",
    amount=0.0,
    debate_type="sequential",
    status="completed",
)
