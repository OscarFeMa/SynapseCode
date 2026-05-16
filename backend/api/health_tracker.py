"""
SynapseCode v2.7 - Health State Tracker
Mantiene estado persistente entre health checks:
- last_error, consecutive_failures, uptime, last_check_time
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ServiceHealthState:
    """Estado persistente de salud de un servicio"""

    name: str
    status: str = "unknown"
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0
    first_check_time: Optional[float] = None
    last_check_time: Optional[float] = None
    last_ok_time: Optional[float] = None
    uptime_seconds: float = 0.0
    avg_response_ms: float = 0.0
    _response_times: list = field(default_factory=list)

    @property
    def failure_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.total_failures / self.total_checks

    @property
    def is_healthy(self) -> bool:
        return self.status in ("healthy", "online", "available", "skipped")

    def record_check(self, status: str, error: Optional[str] = None, response_ms: float = 0.0):
        now = time.time()
        self.total_checks += 1
        self.last_check_time = now
        self.status = status
        self._response_times.append(response_ms)
        if len(self._response_times) > 100:
            self._response_times = self._response_times[-100:]
        self.avg_response_ms = sum(self._response_times) / len(self._response_times)

        if self.is_healthy:
            self.consecutive_failures = 0
            self.last_ok_time = now
            if self.first_check_time is None:
                self.first_check_time = now
            if self.last_ok_time and self.first_check_time:
                self.uptime_seconds = self.last_ok_time - self.first_check_time
        else:
            self.consecutive_failures += 1
            self.total_failures += 1
            self.last_error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "lastError": self.last_error,
            "consecutiveFailures": self.consecutive_failures,
            "failureRate": round(self.failure_rate * 100, 1),
            "uptimeSeconds": round(self.uptime_seconds, 1),
            "avgResponseMs": round(self.avg_response_ms, 1),
            "totalChecks": self.total_checks,
            "lastCheckTime": self.last_check_time,
            "lastOkTime": self.last_ok_time,
        }


class HealthStateTracker:
    """Singleton que mantiene estado de salud de todos los servicios"""

    _instance: Optional["HealthStateTracker"] = None
    _states: Dict[str, ServiceHealthState] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_state(self, service_name: str) -> ServiceHealthState:
        if service_name not in self._states:
            self._states[service_name] = ServiceHealthState(name=service_name)
        return self._states[service_name]

    def record(
        self,
        service_name: str,
        status: str,
        error: Optional[str] = None,
        response_ms: float = 0.0,
    ):
        state = self.get_state(service_name)
        state.record_check(status, error, response_ms)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        return {name: state.to_dict() for name, state in self._states.items()}

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._states)
        healthy = sum(1 for s in self._states.values() if s.is_healthy)
        degraded = sum(1 for s in self._states.values() if s.consecutive_failures > 0 and s.status != "skipped")

        return {
            "totalServices": total,
            "healthyServices": healthy,
            "degradedServices": degraded,
            "overallHealth": "healthy" if degraded == 0 else "degraded",
        }

    def reset(self):
        """Resetea todo el estado (util para tests)"""
        self._states.clear()


health_tracker = HealthStateTracker()
