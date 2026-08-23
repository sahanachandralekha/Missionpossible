"""Normalized Opportunity data models.

This module defines the central OpportunityInput contract which represents an
opportunity regardless of whether it originally arrived as plain text, an image/screenshot,
or a PDF document.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    """Supported input source types for ScamCheck."""
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"


class ProcessingStatus(str, Enum):
    """Lifecycle status of input extraction and normalization."""
    PENDING = "pending"
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    FAILED = "failed"


class OpportunityInput(BaseModel):
    """Normalized internal representation of an opportunity submission.
    
    All input formats (plain text, screenshot/image, PDF document) are normalized
    into this common representation prior to passing to downstream analysis layers.
    
    Attributes:
        source_type: The original format type (text, image, or pdf).
        original_filename: The name of the file if uploaded, otherwise None.
        mime_type: The MIME type of the input (e.g. text/plain, image/png, application/pdf).
        raw_text: The initial raw text before normalization (if text) or OCR raw output.
        extracted_text: Cleaned and normalized text content ready for downstream analysis.
        metadata: Contextual attributes (e.g. file size, platform hint, timestamp).
        processing_status: Current status of the input through the normalization pipeline.
    """

    source_type: SourceType = Field(
        ...,
        description="Origin source format of the opportunity: text, image, or pdf"
    )
    original_filename: Optional[str] = Field(
        default=None,
        description="Original uploaded filename when applicable"
    )
    mime_type: Optional[str] = Field(
        default=None,
        description="MIME type of the source data"
    )
    raw_text: Optional[str] = Field(
        default=None,
        description="Raw un-normalized text or raw OCR extraction"
    )
    extracted_text: str = Field(
        ...,
        description="Normalized extracted text ready for downstream ML and risk evaluation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Auxiliary metadata such as platform hints, file size, or OCR confidence"
    )
    processing_status: ProcessingStatus = Field(
        default=ProcessingStatus.NORMALIZED,
        description="Current processing state of the normalized record"
    )


class TextSubmissionRequest(BaseModel):
    """API payload for direct text submission."""
    text: str = Field(
        ...,
        min_length=1,
        description="Raw text content of the opportunity received by the user"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional client metadata (e.g. channel: WhatsApp, LinkedIn)"
    )

    @field_validator("text")
    @classmethod
    def validate_non_empty_text(cls, v: str) -> str:
        """Ensure submitted text is non-empty and contains non-whitespace characters."""
        if not isinstance(v, str):
            raise ValueError("Input text must be a string")
        if not v.strip():
            raise ValueError("Input text cannot be empty or whitespace only")
        return v


class AnalysisResponsePlaceholder(BaseModel):
    """API response foundation for analysis requests.
    
    NOTE: In this foundation phase, risk scoring and ML classification are not executed.
    This schema acknowledges successful normalization and readiness for downstream layers.
    """
    status: str = "success"
    message: str
    normalized_input: OpportunityInput
    note: str = "Architecture foundation established. Downstream ML and Risk Engine will be attached in subsequent phases."


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    service: str = "ScamCheck API"
    version: str = "0.1.0"
    stage: str = "foundation"
