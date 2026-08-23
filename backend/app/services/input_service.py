"""Input Service Orchestrator.

This service is responsible solely for:
1. Receiving raw opportunity inputs (plain text or uploaded files).
2. Detecting or verifying the input format.
3. Routing the payload to the corresponding format processor.
4. Returning a standardized, normalized OpportunityInput data model.

Architectural Rule:
This service does NOT perform ML classification, rule evaluation, or risk scoring.
Its boundary is strictly restricted to ingestion, validation, and normalization.
"""

from typing import Any, Dict, Optional
from backend.app.processors.image_processor import ImageProcessor
from backend.app.processors.pdf_processor import PdfProcessor
from backend.app.processors.text_processor import TextProcessor
from backend.app.schemas.opportunity import OpportunityInput, SourceType


class InputService:
    """Orchestration service for multi-format opportunity intake."""

    def __init__(
        self,
        text_processor: Optional[TextProcessor] = None,
        image_processor: Optional[ImageProcessor] = None,
        pdf_processor: Optional[PdfProcessor] = None,
    ) -> None:
        self.text_processor = text_processor or TextProcessor()
        self.image_processor = image_processor or ImageProcessor()
        self.pdf_processor = pdf_processor or PdfProcessor()

    def process_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OpportunityInput:
        """Process plain text opportunity input."""
        return self.text_processor.process(
            content=text,
            filename=None,
            mime_type="text/plain",
            metadata=metadata,
        )

    def detect_source_type(
        self,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> SourceType:
        """Determine whether an uploaded file is an image or PDF based on MIME type and extension."""
        mime = (mime_type or "").lower().strip()
        name = (filename or "").lower().strip()

        if mime.startswith("image/") or any(
            name.endswith(ext) for ext in ImageProcessor.SUPPORTED_EXTENSIONS
        ):
            return SourceType.IMAGE

        if mime in PdfProcessor.SUPPORTED_MIME_TYPES or name.endswith(".pdf"):
            return SourceType.PDF

        raise ValueError(
            f"Unsupported file format for '{filename or 'uploaded file'}' (MIME: {mime_type or 'unknown'}). "
            "Supported formats: Images (.png, .jpg, .jpeg, .webp) and PDF documents (.pdf)."
        )

    def process_file(
        self,
        content: bytes,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OpportunityInput:
        """Detect file type and route binary content to the corresponding processor."""
        source_type = self.detect_source_type(filename=filename, mime_type=mime_type)

        if source_type == SourceType.IMAGE:
            return self.image_processor.process(
                content=content,
                filename=filename,
                mime_type=mime_type,
                metadata=metadata,
            )
        elif source_type == SourceType.PDF:
            return self.pdf_processor.process(
                content=content,
                filename=filename,
                mime_type=mime_type,
                metadata=metadata,
            )
        else:
            raise ValueError(f"No processor registered for source type: {source_type}")
