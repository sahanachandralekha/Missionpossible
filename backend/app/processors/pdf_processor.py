"""PDF Document Input Processor.

STATUS: FULLY IMPLEMENTED (Part 4)

Pipeline Flow:
Uploaded PDF Bytes
        ↓
Format & Byte Validation (Extension, MIME, Size ≤ 15MB, Non-empty)
        ↓
PDF Service (pypdf in-memory inspection & page-by-page text extraction)
        ↓
Multi-Page Assembly (Deterministic page boundary markers)
        ↓
TextProcessor (Conservative Normalization & Evidence Preservation)
        ↓
OpportunityInput (source_type = "pdf")

Architectural Guarantees:
- Uses free, pure-Python pypdf text extraction engine.
- Extracted PDF text flows directly through the existing TextProcessor.
- 100% preserves URLs, emails, phone numbers, currency symbols, percentages, dates, and casing.
- Ephemeral in-memory processing (zero permanent disk storage of uploaded PDFs).
"""

from typing import Any, Dict, Optional, Set
from backend.app.processors.base import BaseInputProcessor
from backend.app.processors.text_processor import TextProcessor
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType
from backend.app.services.pdf_service import PDFExtractionResult, PDFService


class PdfProcessor(BaseInputProcessor):
    """Processor for PDF document opportunity submissions (e.g. offer letters, flyers, brochures)."""

    MAX_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB limit
    SUPPORTED_EXTENSIONS: Set[str] = {".pdf"}
    SUPPORTED_MIME_TYPES: Set[str] = {
        "application/pdf",
        "application/x-pdf",
        "application/acrobat",
        "applications/vnd.pdf",
        "text/pdf",
        "text/x-pdf",
    }

    def __init__(
        self,
        pdf_service: Optional[PDFService] = None,
        text_processor: Optional[TextProcessor] = None,
    ) -> None:
        self.pdf_service = pdf_service or PDFService()
        self.text_processor = text_processor or TextProcessor()

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
                f"PDF size ({len(content):,} bytes) exceeds the limit of {self.MAX_FILE_SIZE_BYTES:,} bytes (15 MB)"
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
        """Validate PDF bytes, extract embedded text, normalize, and produce OpportunityInput."""
        # 1. Validate format, size, and extensions
        self.validate(content=content, filename=filename, mime_type=mime_type)

        # 2. Extract embedded text via PDFService
        extract_result: PDFExtractionResult = self.pdf_service.extract_text_from_bytes(content)

        # 3. Base metadata accumulation
        meta = dict(metadata or {})
        meta.update({
            "byte_size": len(content),
            "pdf_page_count": extract_result.page_count,
            "pdf_extraction_engine": extract_result.engine,
            "pdf_status": extract_result.status,
            "file_type": "pdf",
        })
        if extract_result.pdf_title:
            meta["pdf_title"] = extract_result.pdf_title
        if extract_result.pdf_author:
            meta["pdf_author"] = extract_result.pdf_author

        # 4. Handle Password-Protected / Encrypted PDF
        if extract_result.status == "password_protected":
            return OpportunityInput(
                source_type=SourceType.PDF,
                original_filename=filename,
                mime_type=mime_type or "application/pdf",
                raw_text=None,
                extracted_text="[PDF_PASSWORD_PROTECTED: This PDF document is password-protected. Text extraction requires decryption.]",
                metadata=meta,
                processing_status=ProcessingStatus.FAILED,
            )

        # 5. Handle No Extractable Text (Scanned image PDF or empty document)
        if extract_result.status == "no_extractable_text" or not extract_result.raw_text.strip():
            meta["pdf_status"] = "no_extractable_text"
            return OpportunityInput(
                source_type=SourceType.PDF,
                original_filename=filename,
                mime_type=mime_type or "application/pdf",
                raw_text=None,
                extracted_text="[PDF_NO_EXTRACTABLE_TEXT: No digital embedded text layer could be found in this PDF document. Scanned document OCR is scheduled for a future enhancement.]",
                metadata=meta,
                processing_status=ProcessingStatus.FAILED,
            )

        # 6. Pass raw extracted PDF text through the existing TextProcessor
        normalized_text = self.text_processor.normalize_text(extract_result.raw_text)

        # Add text metrics from normalization
        meta.update({
            "char_count": len(normalized_text),
            "word_count": len(normalized_text.split()),
            "line_count": len(normalized_text.splitlines()),
        })

        # 7. Return unified OpportunityInput record
        return OpportunityInput(
            source_type=SourceType.PDF,
            original_filename=filename,
            mime_type=mime_type or "application/pdf",
            raw_text=extract_result.raw_text,
            extracted_text=normalized_text,
            metadata=meta,
            processing_status=ProcessingStatus.NORMALIZED,
        )
