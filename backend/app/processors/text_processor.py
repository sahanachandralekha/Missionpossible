"""Text Input Processor.

STATUS: IMPLEMENTED

Responsible for validating direct text input, performing basic sanitation
and normalization (stripping leading/trailing whitespace, normalizing line endings,
removing null bytes), and outputting a normalized OpportunityInput model.
"""

import re
from typing import Any, Dict, Optional
from backend.app.processors.base import BaseInputProcessor
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType


class TextProcessor(BaseInputProcessor):
    """Processor for user-submitted raw text opportunities.
    
    Performs conservative normalization:
    - Rejects empty, whitespace-only, or oversized inputs
    - Strips dangerous non-printable control characters (while preserving tabs, newlines, emojis, and unicode)
    - Normalizes line breaks (CRLF / CR -> LF)
    - Consolidates excessive consecutive blank lines (3+ -> 2)
    - Strips accidental bounding whitespace
    - Preserves 100% of URLs, emails, phone numbers, currencies, dates, punctuation, and casing
    """

    DEFAULT_MAX_TEXT_LENGTH: int = 100_000  # Configurable 100,000 character safety limit

    def __init__(self, max_text_length: int = DEFAULT_MAX_TEXT_LENGTH) -> None:
        self.max_text_length = max_text_length

    def validate(self, text: Any) -> bool:
        """Validate that input text is a non-empty string within size limits."""
        if not isinstance(text, str):
            raise ValueError("Input text must be a string")
        
        stripped = text.strip()
        if not stripped:
            raise ValueError("Input text cannot be empty or whitespace only")
        
        if len(text) > self.max_text_length:
            raise ValueError(
                f"Input text length ({len(text):,} characters) exceeds maximum allowed limit "
                f"of {self.max_text_length:,} characters"
            )
            
        return True

    def normalize_text(self, text: str) -> str:
        """Perform conservative normalization while strictly preserving all semantic content and evidence."""
        # 1. Remove dangerous non-printable control characters (ASCII 0-8, 11-12, 14-31, 127)
        # Preserve: \t (\x09) and \n (\x0a) and \r (\x0d)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        
        # 2. Standardize line endings (CRLF and CR -> LF)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        
        # 3. Collapse excessive blank lines (more than 2 consecutive newlines -> 2)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        
        # 4. Strip outer bounding whitespace
        return cleaned.strip()

    def process(
        self,
        content: str,
        filename: Optional[str] = None,
        mime_type: Optional[str] = "text/plain",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OpportunityInput:
        """Validate, conservatively normalize, and return an OpportunityInput record."""
        self.validate(content)
        normalized = self.normalize_text(content)
        
        meta = dict(metadata or {})
        meta.setdefault("char_count", len(normalized))
        meta.setdefault("word_count", len(normalized.split()))
        meta.setdefault("line_count", len(normalized.splitlines()))

        return OpportunityInput(
            source_type=SourceType.TEXT,
            original_filename=filename,
            mime_type=mime_type or "text/plain",
            raw_text=content,
            extracted_text=normalized,
            metadata=meta,
            processing_status=ProcessingStatus.NORMALIZED,
        )
