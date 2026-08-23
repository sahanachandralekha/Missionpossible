"""Risk Signal Data Contract for ScamCheck Analysis Layer.

STATUS: FULLY IMPLEMENTED (Analysis Data Contracts)

Purpose:
Represents a single detected risk indicator (e.g. upfront fee, urgency trigger,
free email domain for corporate hiring, unverified domain, semantic ML score).
Designed for multi-signal synthesis and explainable feedback.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.analysis.models.enums import SignalSeverity
from backend.app.analysis.models.evidence import Evidence


class RiskSignal(BaseModel):
    """Structured representation of an individual risk signal."""

    signal_id: str = Field(
        ...,
        description="Unique programmatic identifier for the signal type (e.g. 'SIG_UPFRONT_FEE', 'SIG_URGENT_DEADLINE').",
        examples=["SIG_UPFRONT_FEE", "SIG_OFF_PLATFORM_REDIRECT", "SIG_SUSPICIOUS_DOMAIN"],
    )
    signal_type: str = Field(
        ...,
        description="High-level signal category (e.g. 'financial_risk', 'urgency_coercion', 'identity_verification', 'ml_semantic').",
        examples=["financial_risk", "urgency_coercion", "contact_anomaly"],
    )
    title: str = Field(
        ...,
        description="Human-readable title summarizing the detected indicator.",
        examples=["Upfront Registration Fee Requested", "High-Urgency Coercion Language"],
    )
    description: str = Field(
        ...,
        description="Detailed explanation of what was detected and why it is significant.",
        examples=["The opportunity requests an upfront payment or deposit prior to interview/hiring."],
    )
    severity: SignalSeverity = Field(
        ...,
        description="Severity level of this individual indicator (LOW, MEDIUM, HIGH, CRITICAL).",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence level of this signal detection (0.0 to 1.0).",
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Concrete textual or contextual evidence markers supporting this signal.",
    )
    score_contribution: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Weighted numerical score contribution assigned by the future Risk Engine (0.0 to 100.0).",
    )
    source: str = Field(
        default="rule_engine",
        description="Origin analytical module (e.g. 'text_rule', 'ml_classifier', 'url_analyzer', 'whois_rdap', 'ocr_extractor').",
        examples=["text_rule", "ml_classifier", "url_analyzer"],
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Student-friendly educational takeaway explaining how to safely handle this indicator.",
        examples=["Legitimate employers never ask candidates to pay registration or training fees."],
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Module-specific diagnostic or analytical metadata.",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "signal_id": "SIG_UPFRONT_FEE",
                "signal_type": "financial_risk",
                "title": "Upfront Fee Requested",
                "description": "The opportunity asks for payment before starting.",
                "severity": "high",
                "confidence": 0.95,
                "evidence": [
                    {
                        "type": "payment_amount",
                        "value": "₹999",
                        "source": "text",
                        "context": "Pay ₹999 registration fee immediately",
                    }
                ],
                "source": "text_rule",
                "explanation": "Legitimate internships never require upfront fees.",
            }
        },
    )
