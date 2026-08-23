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
    # Part 7 Rule Signals
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
    # Part 10 URL & Domain Signals
    "SIG_INSECURE_URL": 5.0,
    "SIG_SHORTENED_URL": 15.0,
    "SIG_IP_ADDRESS_URL": 15.0,
    "SIG_URL_USERINFO": 20.0,
    "SIG_UNUSUAL_URL_PORT": 10.0,
    "SIG_EXCESSIVE_URL_LENGTH": 5.0,
    "SIG_SUSPICIOUS_HOSTNAME": 10.0,
    "SIG_SUSPICIOUS_REDIRECT_PARAMETER": 5.0,
    "SIG_DOMAIN_ORGANIZATION_MISMATCH": 10.0,
    # Part 11 Semantic ML/LLM Signals
    "SIG_SEMANTIC_PAYMENT_PRESSURE": 15.0,
    "SIG_SEMANTIC_RECRUITMENT_ANOMALY": 10.0,
    "SIG_SEMANTIC_IMPERSONATION": 15.0,
    "SIG_SEMANTIC_UNREALISTIC_PROMISE": 15.0,
    "SIG_SEMANTIC_SOCIAL_ENGINEERING": 15.0,
    "SIG_SEMANTIC_IDENTITY_REQUEST": 10.0,
    "SIG_SEMANTIC_FINANCIAL_MANIPULATION": 15.0,
    "SIG_SEMANTIC_SUSPICIOUS_OPPORTUNITY_CONTEXT": 10.0,
    # Part 12 Domain Verification Signals
    "SIG_DOMAIN_UNRESOLVED": 5.0,
    "SIG_DOMAIN_REDIRECT_ANOMALY": 10.0,
    "SIG_DOMAIN_ORGANIZATION_INCONSISTENCY": 10.0,
    "SIG_DOMAIN_TLS_ANOMALY": 5.0,
    "SIG_DOMAIN_REGISTRATION_ANOMALY": 10.0,
    "SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE": 5.0,
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
