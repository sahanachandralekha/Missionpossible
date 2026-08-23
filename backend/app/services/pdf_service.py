"""Dedicated PDF Document Text Extraction Service.

STATUS: FULLY IMPLEMENTED (Part 4)

Technology: pypdf
- 100% Free, pure-Python, and locally runnable without cloud API keys or external binaries.
- Safe in-memory decoding and page-by-page text extraction.
- Detects encryption / password protection without bypassing security.
- Captures document metadata (page count, title, author, creation date).

Single Responsibility:
PDF BYTES -> DECODE & INSPECT -> EMBEDDED TEXT EXTRACTION -> STRUCTURED RESULT

Architectural Boundary:
Does NOT determine risk, classify scams, execute ML analysis, or make network requests.
"""

import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pypdf
from pypdf.errors import PdfReadError


@dataclass
class PDFExtractionResult:
    """Structured result from PDF text extraction."""
    raw_text: str
    page_count: int
    status: str  # "success", "no_extractable_text", "password_protected", "failed"
    is_encrypted: bool = False
    pdf_title: Optional[str] = None
    pdf_author: Optional[str] = None
    pdf_creation_date: Optional[str] = None
    engine: str = "pypdf"
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFService:
    """Service for parsing and extracting embedded text layers from PDF documents."""

    DEFAULT_MAX_PAGE_COUNT: int = 100  # Safety limit against PDF page-bomb attacks

    def __init__(self, max_pages: int = DEFAULT_MAX_PAGE_COUNT) -> None:
        self.max_pages = max_pages

    def validate_pdf_bytes(self, content: bytes) -> None:
        """Perform perimeter validation on PDF binary header and size."""
        if not content or len(content) == 0:
            raise ValueError("Uploaded PDF file is empty (0 bytes)")

        # Verify PDF magic signature within initial 1024 bytes (standard allows small prefix)
        if b"%PDF-" not in content[:1024]:
            raise ValueError("Invalid PDF file: Missing standard %PDF- header signature")

    def extract_text_from_bytes(self, content: bytes) -> PDFExtractionResult:
        """Extract embedded digital text and metadata from PDF bytes.
        
        Args:
            content: Raw binary bytes of the PDF document.
            
        Returns:
            PDFExtractionResult with extracted text, page count, and status.
            
        Raises:
            ValueError: If the PDF is malformed, corrupted, or exceeds safety limits.
        """
        self.validate_pdf_bytes(content)

        try:
            stream = io.BytesIO(content)
            reader = pypdf.PdfReader(stream)

            # 1. Encryption / Password Check
            if reader.is_encrypted:
                # Attempt empty password decryption (standard for some PDF viewers)
                try:
                    decrypt_status = reader.decrypt("")
                    if decrypt_status == pypdf.PasswordType.NOT_DECRYPTED:
                        return PDFExtractionResult(
                            raw_text="",
                            page_count=0,
                            status="password_protected",
                            is_encrypted=True,
                            engine="pypdf",
                        )
                except Exception:
                    return PDFExtractionResult(
                        raw_text="",
                        page_count=0,
                        status="password_protected",
                        is_encrypted=True,
                        engine="pypdf",
                    )

            # 2. Page Count Inspection & Safety Boundary
            total_pages = len(reader.pages)
            if total_pages == 0:
                return PDFExtractionResult(
                    raw_text="",
                    page_count=0,
                    status="no_extractable_text",
                    is_encrypted=False,
                    engine="pypdf",
                )

            if total_pages > self.max_pages:
                raise ValueError(
                    f"PDF page count ({total_pages} pages) exceeds the maximum allowed safety limit "
                    f"of {self.max_pages} pages"
                )

            # 3. Extract Document Metadata (Contextual only, not used for risk scoring)
            doc_info = reader.metadata or {}
            title = str(doc_info.get("/Title")) if doc_info.get("/Title") else None
            author = str(doc_info.get("/Author")) if doc_info.get("/Author") else None
            creation_date = str(doc_info.get("/CreationDate")) if doc_info.get("/CreationDate") else None

            # 4. Page-by-Page Text Extraction & Assembly
            page_text_blocks: List[str] = []
            extracted_pages_with_content = 0

            for idx, page in enumerate(reader.pages, start=1):
                try:
                    page_content = page.extract_text() or ""
                    cleaned_page = page_content.strip()
                    if cleaned_page:
                        extracted_pages_with_content += 1
                        # Include deterministic page header boundary for multi-page documents
                        if total_pages > 1:
                            page_text_blocks.append(f"--- Page {idx} ---\n{cleaned_page}")
                        else:
                            page_text_blocks.append(cleaned_page)
                except Exception:
                    # In case of minor per-page font decoding error, continue to next page
                    continue

            # 5. Check if any readable embedded text was recovered
            if not page_text_blocks or extracted_pages_with_content == 0:
                return PDFExtractionResult(
                    raw_text="",
                    page_count=total_pages,
                    status="no_extractable_text",
                    is_encrypted=False,
                    pdf_title=title,
                    pdf_author=author,
                    pdf_creation_date=creation_date,
                    engine="pypdf",
                    metadata={"pages_with_text": 0},
                )

            assembled_text = "\n\n".join(page_text_blocks)

            return PDFExtractionResult(
                raw_text=assembled_text,
                page_count=total_pages,
                status="success",
                is_encrypted=False,
                pdf_title=title,
                pdf_author=author,
                pdf_creation_date=creation_date,
                engine="pypdf",
                metadata={"pages_with_text": extracted_pages_with_content},
            )

        except PdfReadError as e:
            raise ValueError(f"Uploaded PDF is corrupted or cannot be parsed: {str(e)}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Uploaded PDF is invalid or unreadable: {str(e)}")
