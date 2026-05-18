"""
Synapse v2.8 - Circuit Breaker Pattern
Prevents cascading failures when cloud providers are unavailable.
"""

import time
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker for cloud adapters.

    States:
    - CLOSED: Normal operation. Track failures.
    - OPEN: Too many failures. Reject requests immediately.
    - HALF_OPEN: After timeout, allow one test request.

    Transitions:
    - CLOSED -> OPEN: When failure_count >= failure_threshold
    - OPEN -> HALF_OPEN: When recovery_timeout expires
    - HALF_OPEN -> CLOSED: When test request succeeds
    - HALF_OPEN -> OPEN: When test request fails
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.success_count = 0
        self.total_requests = 0
        self.total_failures = 0

    def can_execute(self) -> bool:
        """Check if a request can be executed"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker.transition",
                    name=self.name,
                    from_state="open",
                    to_state="half_open",
                )
                return True
            return False

        # HALF_OPEN: allow one test request
        return True

    def record_success(self):
        """Record a successful request"""
        self.total_requests += 1
        self.success_count += 1

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(
                "circuit_breaker.recovered",
                name=self.name,
                total_failures=self.total_failures,
            )

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success (optional: could use sliding window)
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed request"""
        self.total_requests += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker.half_open_failed",
                name=self.name,
            )

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker.opened",
                    name=self.name,
                    failure_count=self.failure_count,
                    recovery_timeout=self.recovery_timeout,
                )

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": (
                self.success_count / self.total_requests if self.total_requests > 0 else 0
            ),
        }

    def reset(self):
        """Manually reset the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("circuit_breaker.reset", name=self.name)


class CircuitBreakerRegistry:
    """Global registry of circuit breakers per provider"""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str, failure_threshold: int = 3, recovery_timeout: float = 60.0) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return self._breakers[name]

    def get_all_status(self) -> list[dict[str, Any]]:
        """Get status of all circuit breakers"""
        return [cb.get_status() for cb in self._breakers.values()]

    def reset_all(self):
        """Reset all circuit breakers"""
        for cb in self._breakers.values():
            cb.reset()


# Global instance
circuit_breakers = CircuitBreakerRegistry()
