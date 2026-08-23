"""Analysis Result Data Contract for ScamCheck Analysis Layer.

STATUS: FULLY IMPLEMENTED (Analysis Data Contracts)

Purpose:
The final, comprehensive result schema representing an evaluated opportunity.
Contains calibrated risk scores (0-100), risk band (LOW/MEDIUM/HIGH/CRITICAL),
explainable signals, extracted evidence, and student-focused guidance.

Crucial Design Principle:
Never produces binary 'SCAM' vs 'NOT_SCAM' classifications.
All risk conclusions are grounded in explainable signals and evidence.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.enums import AnalysisStatus, RiskLevel
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.schemas.opportunity import SourceType


class AnalysisResult(BaseModel):
    """Complete, explainable result produced by the ScamCheck intelligence layer."""

    opportunity_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier for the opportunity evaluation.",
    )
    source_type: SourceType = Field(
        ...,
        description="Original ingestion modality ('text', 'image', or 'pdf').",
    )
    risk_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Calibrated overall opportunity risk score from 0 (minimal risk) to 100 (critical risk).",
        examples=[15, 55, 88],
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Calibrated risk level band (LOW, MEDIUM, HIGH, CRITICAL).",
        examples=[RiskLevel.LOW, RiskLevel.HIGH],
    )
    signals: List[RiskSignal] = Field(
        default_factory=list,
        description="List of all detected individual risk signals with evidence and severity.",
    )
    extracted_entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities,
        description="Structured entities extracted from the opportunity content.",
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Consolidated list of evidence markers supporting the analysis.",
    )
    summary: Optional[str] = Field(
        default=None,
        description="High-level narrative summary of the opportunity risk assessment.",
        examples=["Opportunity exhibits multiple high-risk indicators including upfront payment demands."],
    )
    student_guidance: Optional[str] = Field(
        default=None,
        description="Actionable educational guidance for students based on the assessed risk level.",
        examples=["Do not make payments or share sensitive documents until verified."],
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Key bulleted takeaway points explaining the risk assessment.",
        examples=[
            "Upfront registration fee requested before joining",
            "High-urgency language pressuring immediate payment",
        ],
    )

    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED,
        description="Execution lifecycle status of the analysis evaluation.",
    )
    model_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata from future ML models (e.g. model_version, inference_time_ms, confidence).",
    )
    analysis_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="General analytical execution metadata (e.g. rules_evaluated_count, execution_time_ms).",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 timestamp string when the analysis was evaluated.",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "source_type": "text",
                "risk_score": 75,
                "risk_level": "high",
                "reasons": [
                    "Upfront registration fee requested",
                    "High-urgency pressure language detected",
                ],
                "summary": "This opportunity asks for an upfront fee of ₹999 which is typical of job scams.",
                "signals": [
                    {
                        "signal_id": "SIG_UPFRONT_FEE",
                        "signal_type": "financial_risk",
                        "title": "Upfront Registration Fee",
                        "description": "Requests ₹999 payment before candidate starts work.",
                        "severity": "high",
                        "confidence": 0.95,
                        "score_contribution": 45.0,
                        "source": "text_rule",
                        "explanation": "Legitimate employers never charge candidates registration fees.",
                    }
                ],
                "status": "completed",
            }
        },
    )
