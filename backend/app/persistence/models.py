"""Persistence models and serialization schemas for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 14)

Defines:
- AnalysisRecord: Complete persistent database entity for an opportunity assessment
- AnalysisSummaryItem: Compact overview record for history list views and pagination
- JSON serialization and reconstruction helpers
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.enums import AnalysisStatus, RiskLevel
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.schemas.opportunity import SourceType


class AnalysisSummaryItem(BaseModel):
    """Compact summary of an analysis for history listings and dashboards."""

    analysis_id: str = Field(..., description="Unique persistent identifier for the analysis.")
    request_id: str = Field(..., description="Traceable correlation ID.")
    created_at: str = Field(..., description="ISO UTC timestamp string when created.")
    completed_at: Optional[str] = Field(None, description="ISO UTC timestamp string when completed.")
    status: AnalysisStatus = Field(..., description="Lifecycle status of the analysis.")
    source_type: SourceType = Field(..., description="Ingestion modality ('text', 'image', 'pdf').")
    risk_score: Optional[int] = Field(None, description="Assessed risk score (0-100).")
    risk_level: RiskLevel = Field(..., description="Assessed risk band ('low', 'medium', 'high', 'critical').")
    summary: Optional[str] = Field(None, description="High-level assessment summary.")
    signals_count: int = Field(default=0, description="Total number of risk signals detected.")

    model_config = ConfigDict(populate_by_name=True)


class AnalysisRecord(BaseModel):
    """Complete persistent database representation of an analysis evaluation."""

    analysis_id: str = Field(..., description="Unique persistent identifier.")
    request_id: str = Field(..., description="Traceable correlation ID.")
    created_at: str = Field(..., description="ISO UTC timestamp string.")
    completed_at: Optional[str] = Field(None, description="ISO UTC timestamp string.")
    status: AnalysisStatus = Field(default=AnalysisStatus.COMPLETED)
    source_type: SourceType = Field(...)
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    summary: Optional[str] = Field(None)
    student_guidance: Optional[str] = Field(None)
    reasons: List[str] = Field(default_factory=list)
    signals: List[RiskSignal] = Field(default_factory=list)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    evidence: List[Evidence] = Field(default_factory=list)
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

    def to_summary(self) -> AnalysisSummaryItem:
        """Convert full record into compact summary item."""
        return AnalysisSummaryItem(
            analysis_id=self.analysis_id,
            request_id=self.request_id,
            created_at=self.created_at,
            completed_at=self.completed_at,
            status=self.status,
            source_type=self.source_type,
            risk_score=self.risk_score,
            risk_level=self.risk_level,
            summary=self.summary,
            signals_count=len(self.signals),
        )


class AnalysisListResponse(BaseModel):
    """Paginated list response for analysis history."""

    total: int = Field(..., description="Total number of matching analysis records.")
    items: List[AnalysisSummaryItem] = Field(default_factory=list, description="Paginated items.")
    limit: int = Field(..., description="Page size limit.")
    offset: int = Field(..., description="Pagination offset.")
