"""PDF Document Input Processor.

STATUS:
- Validation & Interface Structure: IMPLEMENTED
- PDF Text Layer Extraction & Scanned Document OCR: PLANNED (to be integrated in future phase)

Future responsibility:
- Validate uploaded PDF files (format, page limits, file size, mime).
- Extract digital text layer.
- Detect scanned/image-only PDF pages and route to OCR engine.
- Normalize consolidated text into an OpportunityInput record.
"""

from typing import Any, Dict, Optional, Set
from backend.app.processors.base import BaseInputProcessor
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType


class PdfProcessor(BaseInputProcessor):
    """Processor for PDF document opportunity submissions (e.g. offer letters, flyers, brochures)."""

    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB limit
    SUPPORTED_EXTENSIONS: Set[str] = {".pdf"}
    SUPPORTED_MIME_TYPES: Set[str] = {"application/pdf", "application/x-pdf"}

    def validate(
        self,
        content: bytes,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> bool:
        """Validate PDF binary content, size limits, and format attributes."""
        if not isinstance(content, (bytes, bytearray)):
            raise ValueError("PDF content must be binary bytes")
            
        if len(content) == 0:
            raise ValueError("Uploaded PDF file is empty (0 bytes)")
            
        if len(content) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"PDF size ({len(content)} bytes) exceeds the limit of {self.MAX_FILE_SIZE_BYTES} bytes"
            )

        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in self.SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported PDF extension '{ext}'. Supported extensions: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
                )

        if mime_type and mime_type.lower() not in self.SUPPORTED_MIME_TYPES:
            raise ValueError(
                f"Unsupported PDF MIME type '{mime_type}'. Supported MIME types: {', '.join(sorted(self.SUPPORTED_MIME_TYPES))}"
            )

        return True

    def process(
        self,
        content: bytes,
        filename: Optional[str] = None,
        mime_type: Optional[str] = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OpportunityInput:
        """Validate PDF input and produce an OpportunityInput record.
        
        Note: Actual text extraction from digital PDF streams and OCR for scanned documents
        is a PLANNED feature for a subsequent phase. In this foundation architecture, it
        establishes the valid record structure and processing contract.
        """
        self.validate(content=content, filename=filename, mime_type=mime_type)

        meta = dict(metadata or {})
        meta.update({
            "byte_size": len(content),
            "pdf_extraction_status": "planned_placeholder",
            "file_type": "pdf",
        })

        # PLANNED: Future PDF parser integration will populate extracted_text
        placeholder_extracted_text = (
            f"[PLANNED_PDF_EXTRACTION: PDF document '{filename or 'uploaded_document.pdf'}' accepted. "
            "Native text extraction and scanned OCR fallback scheduled for future phase.]"
        )

        return OpportunityInput(
            source_type=SourceType.PDF,
            original_filename=filename,
            mime_type=mime_type or "application/pdf",
            raw_text=None,
            extracted_text=placeholder_extracted_text,
            metadata=meta,
            processing_status=ProcessingStatus.EXTRACTED,
        )
