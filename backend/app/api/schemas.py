"""API Request and Response Schemas for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 13)

Defines data contracts for the HTTP/API boundary:
- AnalyzeTextRequest: Validated JSON submission for text analysis
- AnalysisApiResponse: Stable frontend-ready serialization of AnalysisResult
- ApiHealthResponse: Minimal, network-free liveness/readiness health status
- ApiErrorResponse: Structured error contract preventing raw stack trace exposure
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.enums import AnalysisStatus, RiskLevel
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.schemas.opportunity import SourceType


MAX_TEXT_LENGTH: int = 100_000


class AnalyzeTextRequest(BaseModel):
    """API payload for analyzing plain text opportunities."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Raw text content of the opportunity (e.g. email, WhatsApp message, job post).",
        examples=["Congratulations! You are selected for a remote internship. Pay ₹1,999 registration fee."],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional client metadata (e.g. channel: WhatsApp, platform: LinkedIn).",
    )
    request_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional client-supplied correlation ID for tracing.",
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Input text must be a string.")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Input text cannot be empty or whitespace only.")
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(f"Input text exceeds maximum allowed length of {MAX_TEXT_LENGTH} characters.")
        return v

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                return None
            if not re.match(r"^[a-zA-Z0-9_-]{1,128}$", v_clean):
                raise ValueError("request_id must be alphanumeric and may only contain hyphens and underscores (max 128 chars).")
            return v_clean
        return None


class AnalysisApiResponse(BaseModel):
    """Stable, production-ready API response representation of AnalysisResult."""

    request_id: str = Field(
        ...,
        description="Unique traceable request/correlation identifier.",
        examples=["req_9b1deb4d3b7d4e8b8c5e"],
    )
    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED,
        description="Lifecycle status of the analysis execution ('completed', 'failed', 'processing').",
    )
    source_type: SourceType = Field(
        ...,
        description="Ingestion modality ('text', 'image', or 'pdf').",
    )
    risk_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Calibrated overall opportunity risk score from 0 (minimal risk) to 100 (critical risk).",
        examples=[75],
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Calibrated risk level band ('low', 'medium', 'high', 'critical').",
        examples=[RiskLevel.HIGH],
    )
    summary: Optional[str] = Field(
        default=None,
        description="High-level narrative summary of the risk assessment.",
        examples=["Opportunity exhibits multiple high-risk indicators including upfront payment demands."],
    )
    student_guidance: Optional[str] = Field(
        default=None,
        description="Actionable educational guidance for students.",
        examples=["Do not make payments or share sensitive documents until verified."],
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Key bulleted takeaway points explaining the risk assessment.",
        examples=["Upfront registration fee requested before joining"],
    )
    signals: List[RiskSignal] = Field(
        default_factory=list,
        description="List of detected individual risk signals with evidence and severity.",
    )
    extracted_entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities,
        description="Structured entities extracted from the opportunity content.",
    )
    evidence: List[Evidence] = Field(
        default_factory=list,
        description="Consolidated list of evidence markers supporting the analysis.",
    )
    analysis_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution diagnostic metadata (counts, provider status, execution timing).",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp string.",
    )

    model_config = ConfigDict(populate_by_name=True)


class ApiHealthResponse(BaseModel):
    """API health status contract for monitoring and readiness probes."""

    status: str = Field(default="healthy", description="Service health state.")
    service: str = Field(default="ScamCheck API", description="Service name.")
    version: str = Field(default="1.0.0", description="API version.")
    stage: str = Field(default="production_ready", description="Deployment phase.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the health check.",
    )


class ApiErrorResponse(BaseModel):
    """Structured error response contract."""

    status: str = Field(default="error", description="Error status identifier.")
    error_code: str = Field(..., description="Short machine-readable error category.")
    message: str = Field(..., description="Human-readable explanation of the error.")
    request_id: Optional[str] = Field(default=None, description="Traceable correlation ID.")


# Re-export persistence schemas for API convenience
from backend.app.persistence.models import (
    AnalysisListResponse,
    AnalysisRecord,
    AnalysisSummaryItem,
)

