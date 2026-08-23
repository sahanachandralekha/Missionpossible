"""Lightweight Operational Metrics & Telemetry for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 16)

Provides in-memory operational metrics counters and timers for API diagnostics.
NOTE: Zero influence on RiskScoringEngine, risk_score, risk_level, signals, or evidence.
"""

import threading
import time
from typing import Any, Dict


class MetricsCollector:
    """Thread-safe operational telemetry collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests: int = 0
        self._total_successful_analyses: int = 0
        self._total_failed_analyses: int = 0
        self._total_persistence_saved: int = 0
        self._total_persistence_failures: int = 0
        self._total_provider_failures: int = 0
        self._request_durations_sum: float = 0.0
        self._analysis_durations_sum: float = 0.0

    def record_request(self, duration_seconds: float, status_code: int) -> None:
        """Record an API request duration and status."""
        with self._lock:
            self._total_requests += 1
            self._request_durations_sum += duration_seconds

    def record_analysis(self, duration_seconds: float, success: bool = True) -> None:
        """Record an analysis run timing and outcome."""
        with self._lock:
            if success:
                self._total_successful_analyses += 1
            else:
                self._total_failed_analyses += 1
            self._analysis_durations_sum += duration_seconds

    def record_persistence(self, success: bool = True) -> None:
        """Record a database save outcome."""
        with self._lock:
            if success:
                self._total_persistence_saved += 1
            else:
                self._total_persistence_failures += 1

    def record_provider_failure(self, provider_name: str) -> None:
        """Record a third-party / external provider failure."""
        with self._lock:
            self._total_provider_failures += 1

    def get_summary(self) -> Dict[str, Any]:
        """Return diagnostic metrics snapshot."""
        with self._lock:
            avg_req = (
                self._request_durations_sum / self._total_requests
                if self._total_requests > 0
                else 0.0
            )
            total_anal = self._total_successful_analyses + self._total_failed_analyses
            avg_anal = (
                self._analysis_durations_sum / total_anal
                if total_anal > 0
                else 0.0
            )
            return {
                "total_requests": self._total_requests,
                "avg_request_duration_ms": round(avg_req * 1000, 2),
                "successful_analyses": self._total_successful_analyses,
                "failed_analyses": self._total_failed_analyses,
                "avg_analysis_duration_ms": round(avg_anal * 1000, 2),
                "persistence_saved": self._total_persistence_saved,
                "persistence_failures": self._total_persistence_failures,
                "provider_failures": self._total_provider_failures,
            }

    def reset(self) -> None:
        """Reset all metrics counters (used in testing)."""
        with self._lock:
            self._total_requests = 0
            self._total_successful_analyses = 0
            self._total_failed_analyses = 0
            self._total_persistence_saved = 0
            self._total_persistence_failures = 0
            self._total_provider_failures = 0
            self._request_durations_sum = 0.0
            self._analysis_durations_sum = 0.0


# Global thread-safe metrics collector singleton
metrics_collector = MetricsCollector()
