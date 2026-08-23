"""Evidence Data Contract for ScamCheck Analysis Layer.

STATUS: FULLY IMPLEMENTED (Analysis Data Contracts)

Purpose:
Represents a concrete piece of extractable or derived proof supporting a risk signal.
Designed for student explainability (e.g. showing exact matched phrases, monetary amounts, or URLs).
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    """Structured piece of evidence supporting an analytical signal or finding."""

    type: str = Field(
        ...,
        description="Category of the evidence (e.g. 'payment_amount', 'urgency_phrase', 'suspicious_domain', 'email_provider').",
        examples=["payment_amount", "urgency_phrase", "email_domain"],
    )
    value: str = Field(
        ...,
        description="The extracted evidence string or value.",
        examples=["₹999", "immediately", "hr@gmail.com"],
    )
    source: str = Field(
        default="text",
        description="Origin source modality or analyzer module (e.g. 'text', 'image_ocr', 'pdf', 'url_analyzer', 'whois_rdap').",
        examples=["text", "image_ocr", "pdf"],
    )
    location: Optional[str] = Field(
        default=None,
        description="Character offset, line index, or page boundary where the evidence was discovered.",
        examples=["line:3", "page:1", "offset:145-152"],
    )
    context: Optional[str] = Field(
        default=None,
        description="Surrounding text snippet providing contextual meaning for explainability.",
        examples=["Please pay registration fee of ₹999 before 6 PM to confirm seat."],
    )
    normalized_value: Optional[str] = Field(
        default=None,
        description="Standardized machine-readable representation of the evidence value.",
        examples=["999.00 INR", "gmail.com"],
    )
    original_value: Optional[str] = Field(
        default=None,
        description="Verbatim raw string prior to any sanitization or extraction adjustments.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional arbitrary analytical metadata specific to the evidence type.",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "type": "payment_amount",
                "value": "₹999",
                "source": "text",
                "context": "Pay ₹999 registration fee immediately",
                "normalized_value": "999 INR",
            }
        },
    )
