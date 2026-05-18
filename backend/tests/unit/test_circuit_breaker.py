"""
Unit tests for Circuit Breaker pattern
"""

import time

from backend.adapters.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry, CircuitState


class TestCircuitBreaker:
    """Pruebas del Circuit Breaker"""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.can_execute() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_recovers_from_half_open(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.can_execute()  # Transition to HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_reopens_from_half_open_on_failure(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.can_execute()  # Transition to HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_reduces_failure_count(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 1  # Reduced by 1
        cb.record_success()
        assert cb.failure_count == 0

    def test_get_status(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        status = cb.get_status()
        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["total_requests"] == 3
        assert status["total_failures"] == 1
        assert status["success_rate"] == 2 / 3

    def test_reset(self):
        cb = CircuitBreaker(name="test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_registry_get_creates_new(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get("test_provider")
        assert cb.name == "test_provider"
        assert cb.state == CircuitState.CLOSED

    def test_registry_returns_same_instance(self):
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("test_provider")
        cb2 = registry.get("test_provider")
        assert cb1 is cb2

    def test_registry_get_all_status(self):
        registry = CircuitBreakerRegistry()
        registry.get("provider_a")
        registry.get("provider_b")
        status_list = registry.get_all_status()
        assert len(status_list) == 2
        names = [s["name"] for s in status_list]
        assert "provider_a" in names
        assert "provider_b" in names

    def test_registry_reset_all(self):
        registry = CircuitBreakerRegistry()
        cb = registry.get("test_provider")
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        registry.reset_all()
        assert cb.state == CircuitState.CLOSED
