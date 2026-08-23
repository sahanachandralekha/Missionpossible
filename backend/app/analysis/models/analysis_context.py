"""Analysis Context Data Contract for ScamCheck Analysis Layer.

STATUS: FULLY IMPLEMENTED (Analysis Data Contracts)

Purpose:
Standard envelope passed between analytical modules (entity extractors, rule evaluators,
ML classifiers, domain/network checkers, and the risk engine).
Ensures clean decoupling and predictable payload exchange across analytical pipelines.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.enums import AnalysisStatus
from backend.app.analysis.models.evidence import Evidence
from backend.app.schemas.opportunity import OpportunityInput


class AnalysisContext(BaseModel):
    """Standardized analytical execution context."""

    opportunity: OpportunityInput = Field(
        ...,
        description="The normalized opportunity input record containing raw and extracted text.",
    )
    extracted_entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities,
        description="Collection of structured entities extracted from the opportunity content.",
    )
    evidence_pool: List[Evidence] = Field(
        default_factory=list,
        description="Consolidated pool of evidence markers gathered across extraction and heuristic modules.",
    )
    source_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata preserved from the ingestion processor (e.g. OCR confidence, page counts).",
    )
    analysis_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic information regarding analyzers invoked, durations, and flags.",
    )
    status: AnalysisStatus = Field(
        default=AnalysisStatus.NOT_STARTED,
        description="Lifecycle status of this analysis context (not_started, processing, completed, partial, failed).",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error description if an analytical component encountered an unrecoverable fault.",
    )

    @property
    def opportunity_input(self) -> OpportunityInput:
        """Alias for opportunity to support flexible caller access."""
        return self.opportunity

    @property
    def entities(self) -> ExtractedEntities:
        """Alias for extracted_entities to support flexible caller access."""
        return self.extracted_entities

    model_config = ConfigDict(populate_by_name=True)


