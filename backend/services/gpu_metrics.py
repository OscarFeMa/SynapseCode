"""
Synapse v2.8 - GPU Metrics Service
Monitorea metricas GPU del Worker para dashboard y diagnostico.
"""

import platform
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
import contextlib

logger = structlog.get_logger()


@dataclass
class GPUMetrics:
    """Snapshot de metricas GPU"""

    timestamp: datetime = field(default_factory=datetime.now)
    memory_used_mb: float = 0.0
    memory_free_mb: float = 0.0
    memory_total_mb: float = 0.0
    memory_used_pct: float = 0.0
    temperature_celsius: float | None = None
    utilization_pct: float | None = None
    power_watts: float | None = None
    power_limit_watts: float | None = None
    fan_speed_pct: float | None = None
    gpu_name: str | None = None
    driver_version: str | None = None
    cuda_version: str | None = None
    processes: list[dict[str, Any]] = field(default_factory=list)
    is_available: bool = False
    error: str | None = None


class GPUMetricsCollector:
    """Colector de metricas GPU via nvidia-smi"""

    def __init__(self):
        self._history: list[GPUMetrics] = []
        self._max_history = 100

    def collect(self) -> GPUMetrics:
        """Recopila metricas GPU actuales"""
        if platform.system() != "Windows" and platform.system() != "Linux":
            return GPUMetrics(error="Unsupported platform")

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.used,memory.free,memory.total,"
                    "temperature.gpu,utilization.gpu,power.draw,power.limit,fan.speed,"
                    "processes.used_gpu_memory",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return GPUMetrics(error=f"nvidia-smi failed: {result.stderr.strip()[:200]}")

            parts = [p.strip() for p in result.stdout.strip().split(",")]
            if len(parts) < 11:
                return GPUMetrics(error="Unexpected nvidia-smi output format")

            name, driver, used, free, total, temp, util, power, power_limit, fan, proc_mem = parts

            used_mb = float(used) if used else 0.0
            free_mb = float(free) if free else 0.0
            total_mb = float(total) if total else 1.0

            metrics = GPUMetrics(
                memory_used_mb=used_mb,
                memory_free_mb=free_mb,
                memory_total_mb=total_mb,
                memory_used_pct=(used_mb / total_mb * 100) if total_mb > 0 else 0.0,
                temperature_celsius=float(temp) if temp else None,
                utilization_pct=float(util) if util else None,
                power_watts=float(power) if power else None,
                power_limit_watts=float(power_limit) if power_limit else None,
                fan_speed_pct=float(fan) if fan else None,
                gpu_name=name if name else None,
                driver_version=driver if driver else None,
                is_available=True,
            )

            # Parse processes (simplified - just memory usage)
            if proc_mem and proc_mem != "N/A":
                with contextlib.suppress(ValueError):
                    metrics.processes = [{"gpu_memory_mb": float(proc_mem)}]

            # Add to history
            self._history.append(metrics)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

            return metrics

        except FileNotFoundError:
            return GPUMetrics(error="nvidia-smi not found (no NVIDIA GPU or driver)")
        except subprocess.TimeoutExpired:
            return GPUMetrics(error="nvidia-smi timed out")
        except Exception as e:
            return GPUMetrics(error=str(e))

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Obtiene historial de metricas"""
        recent = self._history[-limit:] if self._history else []
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "memory_used_mb": m.memory_used_mb,
                "memory_free_mb": m.memory_free_mb,
                "memory_used_pct": m.memory_used_pct,
                "temperature_celsius": m.temperature_celsius,
                "utilization_pct": m.utilization_pct,
            }
            for m in recent
        ]

    def get_summary(self) -> dict[str, Any]:
        """Obtiene resumen estadistico del historial"""
        if not self._history:
            return {"samples": 0}

        recent = self._history[-50:]
        temps = [m.temperature_celsius for m in recent if m.temperature_celsius is not None]
        utils = [m.utilization_pct for m in recent if m.utilization_pct is not None]
        mem_pcts = [m.memory_used_pct for m in recent]

        return {
            "samples": len(recent),
            "time_range": {
                "start": recent[0].timestamp.isoformat(),
                "end": recent[-1].timestamp.isoformat(),
            },
            "temperature": {
                "avg": sum(temps) / len(temps) if temps else None,
                "max": max(temps) if temps else None,
                "min": min(temps) if temps else None,
            },
            "utilization": {
                "avg": sum(utils) / len(utils) if utils else None,
                "max": max(utils) if utils else None,
                "min": min(utils) if utils else None,
            },
            "memory": {
                "avg_pct": sum(mem_pcts) / len(mem_pcts) if mem_pcts else None,
                "max_pct": max(mem_pcts) if mem_pcts else None,
                "min_pct": min(mem_pcts) if mem_pcts else None,
            },
        }


# Singleton instance
_gpu_collector = GPUMetricsCollector()


def get_gpu_collector() -> GPUMetricsCollector:
    """Obtiene el colector singleton"""
    return _gpu_collector
