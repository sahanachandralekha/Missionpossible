"""Centralized Scoring Policy for ScamCheck Risk Engine.

STATUS: FULLY IMPLEMENTED (Part 8)

Defines:
- Centralized rule weight mappings
- Severity multipliers and confidence scaling
- Deterministic 0-100 score-to-RiskLevel calibration bands
- Standardized educational summary and guidance templates
"""

from typing import Dict
from backend.app.analysis.models.enums import RiskLevel, SignalSeverity


# -----------------------------------------------------------------------------
# 1. Base Signal Weights (0 - 100 Scale Calibration)
# -----------------------------------------------------------------------------

RULE_WEIGHTS: Dict[str, float] = {
    "SIG_UPFRONT_PAYMENT": 30.0,
    "SIG_URGENCY_PRESSURE": 15.0,
    "SIG_GUARANTEED_SELECTION": 25.0,
    "SIG_NO_INTERVIEW": 15.0,
    "SIG_NO_EXPERIENCE": 10.0,
    "SIG_UNREALISTIC_EARNINGS": 20.0,
    "SIG_AUTHORITY_CLAIM": 15.0,
    "SIG_INFORMAL_CONTACT_CHANNEL": 10.0,
    "SIG_PERSONAL_PAYMENT_DESTINATION": 25.0,
    "SIG_UNSOLICITED_SELECTION": 15.0,
    "SIG_DOCUMENT_CLAIM": 10.0,
    "SIG_MULTIPLE_HIGH_RISK_PATTERNS": 10.0,  # Bounded compound risk adjustment
}

DEFAULT_BASE_WEIGHT: float = 10.0


# -----------------------------------------------------------------------------
# 2. Severity Multipliers
# -----------------------------------------------------------------------------

SEVERITY_MULTIPLIERS: Dict[SignalSeverity, float] = {
    SignalSeverity.LOW: 0.50,
    SignalSeverity.MEDIUM: 0.75,
    SignalSeverity.HIGH: 1.00,
    SignalSeverity.CRITICAL: 1.00,
}


# -----------------------------------------------------------------------------
# 3. Risk Level Calibration Bands
# -----------------------------------------------------------------------------

def get_risk_level(score: float) -> RiskLevel:
    """Map a clamped 0-100 numerical score into a calibrated RiskLevel band.
    
    Bands:
    - 0 to 24   -> LOW
    - 25 to 49  -> MEDIUM
    - 50 to 74  -> HIGH
    - 75 to 100 -> CRITICAL
    """
    clamped = max(0.0, min(100.0, float(score)))
    if clamped < 25.0:
        return RiskLevel.LOW
    elif clamped < 50.0:
        return RiskLevel.MEDIUM
    elif clamped < 75.0:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


# -----------------------------------------------------------------------------
# 4. Student Guidance and Narrative Summaries
# -----------------------------------------------------------------------------

STUDENT_GUIDANCE_MAP: Dict[RiskLevel, str] = {
    RiskLevel.LOW: (
        "Review the opportunity carefully and verify the employer and application "
        "process before sharing personal information."
    ),
    RiskLevel.MEDIUM: (
        "Proceed cautiously. Verify the employer, contact details, and opportunity "
        "through an independent official source."
    ),
    RiskLevel.HIGH: (
        "Do not make payments or share sensitive documents until the employer and "
        "opportunity have been independently verified."
    ),
    RiskLevel.CRITICAL: (
        "Do not pay or share sensitive information. Verify the employer through its "
        "official website and trusted channels before taking any action."
    ),
}

SUMMARY_MAP: Dict[RiskLevel, str] = {
    RiskLevel.LOW: (
        "No major scam indicators were detected in the available information."
    ),
    RiskLevel.MEDIUM: (
        "Some suspicious indicators were detected. Independent verification is recommended."
    ),
    RiskLevel.HIGH: (
        "Multiple significant scam indicators were detected. Proceed with strong caution."
    ),
    RiskLevel.CRITICAL: (
        "Several severe scam indicators were detected. Do not make payments or share "
        "sensitive information without independent verification."
    ),
}
