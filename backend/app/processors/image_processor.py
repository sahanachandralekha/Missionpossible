"""Image & Screenshot Input Processor.

STATUS: FULLY IMPLEMENTED (Part 3)

Pipeline Flow:
Uploaded Image Bytes
        ↓
Format & Byte Validation (Extension, MIME, Size, Non-empty)
        ↓
Image Decode & Integrity Check (Pillow)
        ↓
OCR Service (RapidOCR ONNX local inference)
        ↓
Raw OCR Text & Confidence Metadata
        ↓
TextProcessor (Conservative Normalization & Evidence Preservation)
        ↓
OpportunityInput (source_type = "image")

Architectural Guarantees:
- Uses free, local, offline RapidOCR engine.
- OCR output passes through the exact same TextProcessor as typed text.
- Preserves all detected URLs, emails, phone numbers, currencies, dates, and casing.
- Ephemeral in-memory processing (zero permanent disk storage of images).
"""

from typing import Any, Dict, Optional, Set
from backend.app.processors.base import BaseInputProcessor
from backend.app.processors.text_processor import TextProcessor
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType
from backend.app.services.ocr_service import OCRResult, OCRService


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

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        text_processor: Optional[TextProcessor] = None,
    ) -> None:
        self.ocr_service = ocr_service or OCRService()
        self.text_processor = text_processor or TextProcessor()

    def validate(
        self,
        content: bytes,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> bool:
        """Validate image binary content, size limits, format attributes, and file integrity."""
        if not isinstance(content, (bytes, bytearray)):
            raise ValueError("Image content must be binary bytes")
            
        if len(content) == 0:
            raise ValueError("Uploaded image file is empty (0 bytes)")
            
        if len(content) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Image size ({len(content):,} bytes) exceeds the limit of {self.MAX_FILE_SIZE_BYTES:,} bytes (10 MB)"
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
        """Validate image bytes, execute OCR, normalize extracted text, and return OpportunityInput."""
        # 1. Validate format, size, and extensions
        self.validate(content=content, filename=filename, mime_type=mime_type)

        # 2. Execute local OCR via OCRService (handles decode & validation)
        ocr_result: OCRResult = self.ocr_service.extract_text_from_bytes(content)

        # 3. Base metadata accumulation
        meta = dict(metadata or {})
        meta.update({
            "byte_size": len(content),
            "image_width": ocr_result.image_width,
            "image_height": ocr_result.image_height,
            "image_format": ocr_result.image_format,
            "ocr_engine": ocr_result.engine,
            "ocr_confidence": ocr_result.confidence_avg,
            "ocr_line_count": ocr_result.line_count,
        })

        # 4. Handle failure case: No text detected in image
        if not ocr_result.success or not ocr_result.text.strip():
            meta["ocr_status"] = "no_text_detected"
            return OpportunityInput(
                source_type=SourceType.IMAGE,
                original_filename=filename,
                mime_type=mime_type or f"image/{ocr_result.image_format.lower()}",
                raw_text=None,
                extracted_text="[OCR_NO_TEXT_DETECTED: No recognizable text could be extracted from the uploaded image.]",
                metadata=meta,
                processing_status=ProcessingStatus.FAILED,
            )

        # 5. Pass OCR raw text through the existing TextProcessor for conservative normalization
        normalized_text = self.text_processor.normalize_text(ocr_result.text)

        # Add text metrics from normalization
        meta.update({
            "ocr_status": "success",
            "char_count": len(normalized_text),
            "word_count": len(normalized_text.split()),
            "line_count": len(normalized_text.splitlines()),
        })

        # 6. Return unified OpportunityInput record
        return OpportunityInput(
            source_type=SourceType.IMAGE,
            original_filename=filename,
            mime_type=mime_type or f"image/{ocr_result.image_format.lower()}",
            raw_text=ocr_result.text,
            extracted_text=normalized_text,
            metadata=meta,
            processing_status=ProcessingStatus.NORMALIZED,
        )
