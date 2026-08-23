"""Data schemas and types for the ScamCheck ML/LLM Semantic Intelligence Layer.

STATUS: FULLY IMPLEMENTED (Part 11)

Defines models for:
- SemanticSignalItem (raw provider detection item)
- SemanticModelOutput (structured output returned by any SemanticModelProvider)
- SemanticProviderConfig (provider runtime configuration)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.analysis.models import SignalSeverity


class SemanticSignalItem(BaseModel):
    """Raw structured semantic signal item produced by a semantic provider."""

    signal_id: str = Field(
        ...,
        description="Standardized semantic signal ID (e.g. SIG_SEMANTIC_PAYMENT_PRESSURE).",
    )
    title: str = Field(
        ...,
        description="Human-readable title of the semantic finding.",
    )
    description: str = Field(
        ...,
        description="Detailed explanation of the semantic context detected.",
    )
    severity: SignalSeverity = Field(
        default=SignalSeverity.MEDIUM,
        description="Severity level of the semantic indicator.",
    )
    confidence: float = Field(
        default=0.75,
        description="Confidence score bounded between 0.0 and 1.0.",
    )

    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.75
        try:
            val = float(v)
            return min(max(val, 0.0), 1.0)
        except (ValueError, TypeError):
            return 0.75

    from pydantic import field_validator
    _validate_confidence = field_validator("confidence", mode="before")(clamp_confidence)

    evidence_text: str = Field(
        ...,
        description="Exact phrase or excerpt supporting the semantic signal.",
    )

    explanation: Optional[str] = Field(
        default=None,
        description="Optional detailed contextual reasoning.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional provider-specific detection metadata.",
    )


class SemanticModelOutput(BaseModel):
    """Structured output returned by a SemanticModelProvider."""

    provider_name: str = Field(
        ...,
        description="Identifier of the semantic provider that performed the analysis.",
    )
    signals: List[SemanticSignalItem] = Field(
        default_factory=list,
        description="List of detected semantic signal items.",
    )
    raw_text_length: int = Field(
        default=0,
        description="Character length of the analyzed opportunity text.",
    )
    processing_time_ms: float = Field(
        default=0.0,
        description="Time taken by the provider to perform semantic inference in milliseconds.",
    )
    is_success: bool = Field(
        default=True,
        description="Whether semantic analysis completed successfully.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if the provider encountered a failure.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider diagnostics or parameters.",
    )
