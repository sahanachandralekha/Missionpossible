"""ScamCheck Risk Scoring Package.

STATUS: FULLY IMPLEMENTED (Part 8)

Exports:
- RiskScoringEngine: Calibrated 0-100 risk scoring synthesis
- get_risk_level: Risk score to RiskLevel band mapper
- RULE_WEIGHTS, SEVERITY_MULTIPLIERS, STUDENT_GUIDANCE_MAP, SUMMARY_MAP
"""

from backend.app.analysis.risk.scoring_engine import RiskScoringEngine
from backend.app.analysis.risk.score_policy import (
    RULE_WEIGHTS,
    SEVERITY_MULTIPLIERS,
    STUDENT_GUIDANCE_MAP,
    SUMMARY_MAP,
    get_risk_level,
)

__all__ = [
    "RiskScoringEngine",
    "RULE_WEIGHTS",
    "SEVERITY_MULTIPLIERS",
    "STUDENT_GUIDANCE_MAP",
    "SUMMARY_MAP",
    "get_risk_level",
]
