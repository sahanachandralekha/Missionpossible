"""Comprehensive tests for the ScamCheck PDF Input & Text Extraction Pipeline.

Part 4 Verification:
- Validates PDF document submissions across single-page and multi-page documents
- Tests in-memory embedded text extraction using pypdf
- Verifies extracted PDF text passes through TextProcessor for conservative normalization
- Confirms preservation of evidence markers: URLs, emails, phones, currencies,
  percentages, dates, and urgency punctuation
- Tests deterministic page-aware assembly for multi-page documents
- Tests edge cases: password-protected PDFs, blank/image-only PDFs (no embedded text),
  corrupted PDFs, oversized files, and page limits
- Verifies API intake via multipart/form-data on POST /api/analyze/file
"""

import io
import pytest
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.processors.pdf_processor import PdfProcessor
from backend.app.processors.text_processor import TextProcessor
from backend.app.schemas.opportunity import (
    OpportunityInput,
    ProcessingStatus,
    SourceType,
)
from backend.app.services.input_service import InputService
from backend.app.services.pdf_service import PDFExtractionResult, PDFService


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


def _generate_test_pdf(
    pages: list[list[str]],
    title: str = "Internship Document",
    author: str = "ScamCheck Test Suite",
) -> bytes:
    """Helper to programmatically generate an in-memory PDF with embedded text across pages."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setTitle(title)
    c.setAuthor(author)

    for page_idx, page_lines in enumerate(pages, start=1):
        y = 750
        for line in page_lines:
            c.drawString(72, y, line)
            y -= 25
        c.showPage()

    c.save()
    return buf.getvalue()


def _generate_encrypted_pdf(password: str = "secret123") -> bytes:
    """Helper to generate a password-protected in-memory PDF."""
    raw_pdf = _generate_test_pdf([["Confidential Internship Offer Letter"]])
    reader = PdfWriter()
    reader.append(io.BytesIO(raw_pdf))
    reader.encrypt(password)
    buf = io.BytesIO()
    reader.write(buf)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. PDF Service Direct Unit Tests
# -----------------------------------------------------------------------------

def test_pdf_service_single_page_extraction():
    """Verify PDFService extracts embedded text and metadata from single-page PDF."""
    service = PDFService()
    pdf_bytes = _generate_test_pdf([
        ["Summer Software Internship", "Stipend: $1,500/month", "Contact: hr@tech.io"]
    ])

    result: PDFExtractionResult = service.extract_text_from_bytes(pdf_bytes)

    assert result.status == "success"
    assert result.page_count == 1
    assert result.is_encrypted is False
    assert result.engine == "pypdf"
    assert "Summer Software Internship" in result.raw_text
    assert "$1,500/month" in result.raw_text


def test_pdf_service_multi_page_assembly_and_boundaries():
    """Verify PDFService extracts and assembles multi-page PDFs with deterministic page headers."""
    service = PDFService()
    pdf_bytes = _generate_test_pdf([
        ["Page 1: Job Description", "Role: Backend Developer"],
        ["Page 2: Requirements & Stipend", "Stipend: 25,000 INR", "Apply at https://careers.co"],
        ["Page 3: Contact Details", "HR Email: apply@careers.co"],
    ])

    result: PDFExtractionResult = service.extract_text_from_bytes(pdf_bytes)

    assert result.status == "success"
    assert result.page_count == 3
    assert "--- Page 1 ---" in result.raw_text
    assert "--- Page 2 ---" in result.raw_text
    assert "--- Page 3 ---" in result.raw_text
    assert "Backend Developer" in result.raw_text
    assert "https://careers.co" in result.raw_text


def test_pdf_service_password_protected_handling():
    """Verify PDFService detects password-protected PDFs and returns password_protected status."""
    service = PDFService()
    encrypted_bytes = _generate_encrypted_pdf("mypassword")

    result: PDFExtractionResult = service.extract_text_from_bytes(encrypted_bytes)

    assert result.status == "password_protected"
    assert result.is_encrypted is True
    assert result.raw_text == ""


def test_pdf_service_no_extractable_text_blank_page():
    """Verify PDFService returns no_extractable_text status for blank PDF."""
    service = PDFService()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)

    result: PDFExtractionResult = service.extract_text_from_bytes(buf.getvalue())

    assert result.status == "no_extractable_text"
    assert result.page_count == 1
    assert result.raw_text == ""


def test_pdf_service_page_limit_enforcement():
    """Verify PDFService rejects PDFs exceeding the configured page limit."""
    service = PDFService(max_pages=3)
    pdf_bytes = _generate_test_pdf([
        ["Page 1"], ["Page 2"], ["Page 3"], ["Page 4"]
    ])

    with pytest.raises(ValueError, match="exceeds the maximum allowed safety limit"):
        service.extract_text_from_bytes(pdf_bytes)


def test_pdf_service_corrupted_pdf_raises_value_error():
    """Verify PDFService raises clean ValueError on corrupted PDF stream."""
    service = PDFService()
    corrupt_pdf = b"%PDF-1.4\n" + b"random_corrupted_payload_garbage"

    with pytest.raises(ValueError, match="corrupted or cannot be parsed|invalid"):
        service.extract_text_from_bytes(corrupt_pdf)


def test_pdf_service_missing_pdf_header_rejected():
    """Verify PDFService rejects non-PDF files that lack standard %PDF- magic signature."""
    service = PDFService()
    not_a_pdf = b"This is just a plain text file pretending to be a PDF."

    with pytest.raises(ValueError, match="Missing standard %PDF- header signature"):
        service.extract_text_from_bytes(not_a_pdf)


# -----------------------------------------------------------------------------
# 2. PdfProcessor Pipeline & Evidence Preservation Tests
# -----------------------------------------------------------------------------

def test_pdf_processor_evidence_urls():
    """Verify PdfProcessor extracts and preserves URLs from PDF documents."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "Apply online at https://recruitment.opportunity.org/internships?id=99",
        "Official submission portal",
    ]])

    opp = processor.process(content=pdf_bytes, filename="offer.pdf")

    assert isinstance(opp, OpportunityInput)
    assert opp.source_type == SourceType.PDF
    assert opp.processing_status == ProcessingStatus.NORMALIZED
    assert "https://recruitment.opportunity.org/internships?id=99" in opp.extracted_text


def test_pdf_processor_evidence_emails():
    """Verify PdfProcessor extracts and preserves email addresses."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "Send your resume to talent.acquisition@global-ventures.io",
        "Subject: Data Science Intern",
    ]])

    opp = processor.process(content=pdf_bytes, filename="internship.pdf")
    assert "talent.acquisition@global-ventures.io" in opp.extracted_text


def test_pdf_processor_evidence_phones():
    """Verify PdfProcessor extracts and preserves phone numbers."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "Direct HR Contact: +91 9876543210",
        "Telegram coordinator: +1 (800) 555-0199",
    ]])

    opp = processor.process(content=pdf_bytes, filename="contact.pdf")
    assert "+91 9876543210" in opp.extracted_text
    assert "+1 (800) 555-0199" in opp.extracted_text


def test_pdf_processor_evidence_currencies_and_amounts():
    """Verify PdfProcessor extracts monetary figures and currency symbols."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "Security Deposit: Rs 2,999 (refundable)",
        "Monthly Stipend: $1,200 USD (EUR 1,100)",
    ]])

    opp = processor.process(content=pdf_bytes, filename="fees.pdf")
    assert "2,999" in opp.extracted_text
    assert "$1,200" in opp.extracted_text or "1,200" in opp.extracted_text


def test_pdf_processor_evidence_percentages_and_numbers():
    """Verify PdfProcessor extracts percentages and numerical metrics."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "Earn up to 45% bonus commission on 10 completed projects.",
    ]])

    opp = processor.process(content=pdf_bytes, filename="commission.pdf")
    assert "45%" in opp.extracted_text
    assert "10" in opp.extracted_text


def test_pdf_processor_evidence_dates():
    """Verify PdfProcessor extracts deadlines and dates."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "Application Deadline: 25/10/2026",
        "Cohort Commencement: November 1st, 2026",
    ]])

    opp = processor.process(content=pdf_bytes, filename="dates.pdf")
    assert "25/10/2026" in opp.extracted_text
    assert "November 1st, 2026" in opp.extracted_text


def test_pdf_processor_evidence_urgency_and_casing():
    """Verify PdfProcessor preserves uppercase emphasis and urgent punctuation."""
    processor = PdfProcessor()
    pdf_bytes = _generate_test_pdf([[
        "URGENT: IMMEDIATE JOINING REQUIRED! PAY NOW!",
    ]])

    opp = processor.process(content=pdf_bytes, filename="urgent.pdf")
    assert "URGENT: IMMEDIATE JOINING REQUIRED! PAY NOW!" in opp.extracted_text


def test_pdf_processor_password_protected_status():
    """Verify PdfProcessor marks password-protected PDFs with FAILED status and clear message."""
    processor = PdfProcessor()
    enc_bytes = _generate_encrypted_pdf("pass123")

    opp = processor.process(content=enc_bytes, filename="encrypted.pdf")

    assert opp.source_type == SourceType.PDF
    assert opp.processing_status == ProcessingStatus.FAILED
    assert opp.metadata["pdf_status"] == "password_protected"
    assert "PDF_PASSWORD_PROTECTED" in opp.extracted_text


def test_pdf_processor_no_extractable_text_status():
    """Verify PdfProcessor marks empty/image-only PDFs with FAILED status and clear placeholder."""
    processor = PdfProcessor()
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)

    opp = processor.process(content=buf.getvalue(), filename="blank.pdf")

    assert opp.source_type == SourceType.PDF
    assert opp.processing_status == ProcessingStatus.FAILED
    assert opp.metadata["pdf_status"] == "no_extractable_text"
    assert "PDF_NO_EXTRACTABLE_TEXT" in opp.extracted_text


# -----------------------------------------------------------------------------
# 3. Security, Validation & Error Handling
# -----------------------------------------------------------------------------

def test_pdf_processor_rejects_empty_file():
    """Verify PdfProcessor rejects 0-byte file with clean ValueError."""
    processor = PdfProcessor()
    with pytest.raises(ValueError, match="empty"):
        processor.process(content=b"", filename="empty.pdf", mime_type="application/pdf")


def test_pdf_processor_rejects_oversized_file():
    """Verify PdfProcessor rejects PDF exceeding 15 MB limit."""
    processor = PdfProcessor()
    oversized = b"%PDF-1.4\n" + b"0" * (15 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="exceeds the limit"):
        processor.process(content=oversized, filename="large.pdf", mime_type="application/pdf")


def test_pdf_processor_rejects_unsupported_extension():
    """Verify PdfProcessor rejects unsupported file extensions."""
    processor = PdfProcessor()
    valid_pdf = _generate_test_pdf([["Valid Text"]])
    with pytest.raises(ValueError, match="Unsupported PDF extension"):
        processor.process(content=valid_pdf, filename="document.docx", mime_type="application/pdf")


def test_pdf_processor_rejects_unsupported_mime():
    """Verify PdfProcessor rejects invalid MIME types."""
    processor = PdfProcessor()
    valid_pdf = _generate_test_pdf([["Valid Text"]])
    with pytest.raises(ValueError, match="Unsupported PDF MIME type"):
        processor.process(content=valid_pdf, filename="document.pdf", mime_type="text/plain")


# -----------------------------------------------------------------------------
# 4. InputService Orchestration & End-to-End Tests
# -----------------------------------------------------------------------------

def test_input_service_routes_pdf_and_normalizes():
    """Verify InputService detects PDF, extracts embedded text, and passes through TextProcessor."""
    service = InputService()
    pdf_bytes = _generate_test_pdf([
        ["Global Tech Research Fellowship 2026"],
        ["Stipend: $2,000/month", "Apply at https://fellowships.globaltech.edu"],
    ])

    opp = service.process_file(
        content=pdf_bytes,
        filename="fellowship_announcement.pdf",
        mime_type="application/pdf",
        metadata={"channel": "Email"},
    )

    assert isinstance(opp, OpportunityInput)
    assert opp.source_type == SourceType.PDF
    assert opp.original_filename == "fellowship_announcement.pdf"
    assert opp.processing_status == ProcessingStatus.NORMALIZED
    assert opp.metadata["pdf_extraction_engine"] == "pypdf"
    assert opp.metadata["pdf_page_count"] == 2
    assert opp.metadata["channel"] == "Email"
    assert opp.metadata["char_count"] > 0
    assert opp.metadata["word_count"] > 0
    assert "Global Tech Research Fellowship 2026" in opp.extracted_text
    assert "https://fellowships.globaltech.edu" in opp.extracted_text


# -----------------------------------------------------------------------------
# 5. REST API Endpoint (/api/analyze/file) PDF Upload Tests
# -----------------------------------------------------------------------------

def test_api_analyze_file_pdf_success(client: TestClient):
    """Verify POST /api/analyze/file uploads PDF, extracts text, and returns OpportunityInput."""
    pdf_bytes = _generate_test_pdf([
        ["Official Internship Appointment Letter", "Company: Apex Software Ltd", "Stipend: $1,000"],
        ["Terms & Conditions", "Contact HR at hr@apexsoftware.com"],
    ])

    files = {"file": ("appointment_letter.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "appointment_letter.pdf" in data["message"]

    norm = data["normalized_input"]
    assert norm["source_type"] == "pdf"
    assert norm["original_filename"] == "appointment_letter.pdf"
    assert norm["mime_type"] == "application/pdf"
    assert norm["metadata"]["pdf_extraction_engine"] == "pypdf"
    assert norm["metadata"]["pdf_page_count"] == 2
    assert "Apex Software Ltd" in norm["extracted_text"]
    assert "hr@apexsoftware.com" in norm["extracted_text"]


def test_api_analyze_file_pdf_corrupted(client: TestClient):
    """Verify POST /api/analyze/file on corrupted PDF returns clean 422 JSON error without traceback."""
    corrupt_pdf = b"%PDF-1.4\ncorrupted_garbage_stream"
    files = {"file": ("corrupt.pdf", io.BytesIO(corrupt_pdf), "application/pdf")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "Traceback" not in response.text
