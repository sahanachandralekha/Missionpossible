"""Controlled enumerations for the ScamCheck analysis layer.

STATUS: FULLY IMPLEMENTED (Analysis Data Contracts)

Design Principles:
- RiskLevel communicates calibrated uncertainty across 4 bands (LOW, MEDIUM, HIGH, CRITICAL).
  Never uses binary "SCAM" / "NOT_SCAM".
- SignalSeverity classifies the severity of individual risk indicators.
  A single HIGH severity signal does not automatically make the entire opportunity HIGH risk.
- AnalysisStatus tracks analytical pipeline lifecycle without conflating extraction errors with fraud.
"""

from enum import Enum


class RiskLevel(str, Enum):
    """Calibrated opportunity risk level bands."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignalSeverity(str, Enum):
    """Severity classification for an individual risk signal."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisStatus(str, Enum):
    """Lifecycle status of the analysis evaluation."""
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
