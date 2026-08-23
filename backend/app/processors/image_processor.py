"""Image & Screenshot Input Processor.

STATUS:
- Validation & Interface Structure: IMPLEMENTED
- OCR Extraction & Vision Pipeline: PLANNED (to be integrated in future phase)

Future responsibility:
- Validate uploaded image files (format, dimensions, size, mime).
- Preprocess image (deskewing, contrast adjustment).
- Extract textual content using an OCR engine.
- Normalize extracted OCR text into an OpportunityInput record.
"""

from typing import Any, Dict, Optional, Set
from backend.app.processors.base import BaseInputProcessor
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType


class ImageProcessor(BaseInputProcessor):
    """Processor for screenshot and photo opportunity submissions."""

    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    SUPPORTED_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".webp"}
    SUPPORTED_MIME_TYPES: Set[str] = {
        "image/png",
        "image/jpeg",
        "image/pjpeg",
        "image/webp",
    }

    def validate(
        self,
        content: bytes,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> bool:
        """Validate image binary content, size limits, and format attributes."""
        if not isinstance(content, (bytes, bytearray)):
            raise ValueError("Image content must be binary bytes")
            
        if len(content) == 0:
            raise ValueError("Uploaded image file is empty (0 bytes)")
            
        if len(content) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Image size ({len(content)} bytes) exceeds the limit of {self.MAX_FILE_SIZE_BYTES} bytes"
            )

        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in self.SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported image extension '{ext}'. Supported extensions: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
                )

        if mime_type and mime_type.lower() not in self.SUPPORTED_MIME_TYPES:
            raise ValueError(
                f"Unsupported image MIME type '{mime_type}'. Supported MIME types: {', '.join(sorted(self.SUPPORTED_MIME_TYPES))}"
            )

        return True

    def process(
        self,
        content: bytes,
        filename: Optional[str] = None,
        mime_type: Optional[str] = "image/png",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OpportunityInput:
        """Validate image input and produce an OpportunityInput record.
        
        Note: The actual OCR text extraction is a PLANNED feature for a subsequent phase.
        In this foundation architecture, it establishes the valid record structure and
        processing contract.
        """
        self.validate(content=content, filename=filename, mime_type=mime_type)

        meta = dict(metadata or {})
        meta.update({
            "byte_size": len(content),
            "ocr_status": "planned_placeholder",
            "file_type": "image",
        })

        # PLANNED: Future OCR integration will populate extracted_text from OCR engine
        placeholder_extracted_text = (
            f"[PLANNED_OCR_EXTRACTION: Image '{filename or 'uploaded_image'}' accepted. "
            "OCR engine integration scheduled for future phase.]"
        )

        return OpportunityInput(
            source_type=SourceType.IMAGE,
            original_filename=filename,
            mime_type=mime_type or "image/png",
            raw_text=None,
            extracted_text=placeholder_extracted_text,
            metadata=meta,
            processing_status=ProcessingStatus.EXTRACTED,
        )
