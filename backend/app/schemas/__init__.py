"""Data schemas and Pydantic models for ScamCheck."""

from backend.app.schemas.opportunity import (
    OpportunityInput,
    ProcessingStatus,
    SourceType,
    TextSubmissionRequest,
    AnalysisResponsePlaceholder,
    HealthResponse,
)

__all__ = [
    "OpportunityInput",
    "SourceType",
    "ProcessingStatus",
    "TextSubmissionRequest",
    "AnalysisResponsePlaceholder",
    "HealthResponse",
]
