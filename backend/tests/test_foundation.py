"""Foundation and Architecture Verification Tests for ScamCheck.

Verifies:
1. Backend package and modules import cleanly.
2. FastAPI app initialization and health endpoints.
3. OpportunityInput model validation across text, image, and pdf types.
4. Schema validation rejection for invalid or malformed data.
5. Base processor interface and concrete processor imports/contracts.
6. TextProcessor normalization behavior.
7. ImageProcessor validation and structure.
8. PdfProcessor validation and structure.
9. InputService orchestration and type detection.
10. API route intake functionality (/api/analyze/text, /api/analyze/file).
"""

import io
import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

# 1. Verification of backend imports
from backend.app.main import app
from backend.app.schemas.opportunity import (
    OpportunityInput,
    ProcessingStatus,
    SourceType,
    TextSubmissionRequest,
    AnalysisResponsePlaceholder,
    HealthResponse,
)
from backend.app.processors.base import BaseInputProcessor
from backend.app.processors.text_processor import TextProcessor
from backend.app.processors.image_processor import ImageProcessor
from backend.app.processors.pdf_processor import PdfProcessor
from backend.app.services.input_service import InputService


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


# ----------------------------------------------------------------------
# 1. Application Initialization & Health Tests
# ----------------------------------------------------------------------

def test_fastapi_app_initialization(client: TestClient):
    """Verify FastAPI initializes and returns healthy status on root and /health."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ScamCheck API"
    assert data["stage"] == "foundation"

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"


# ----------------------------------------------------------------------
# 2. OpportunityInput Schema Tests (Text, Image, PDF)
# ----------------------------------------------------------------------

def test_opportunity_input_text_creation():
    """Verify OpportunityInput creation with valid text data."""
    opp = OpportunityInput(
        source_type=SourceType.TEXT,
        original_filename=None,
        mime_type="text/plain",
        raw_text="Earn $500/day working 1 hour from home. Pay $50 registration fee.",
        extracted_text="Earn $500/day working 1 hour from home. Pay $50 registration fee.",
        metadata={"platform": "WhatsApp"},
        processing_status=ProcessingStatus.NORMALIZED,
    )
    assert opp.source_type == SourceType.TEXT
    assert opp.source_type.value == "text"
    assert opp.extracted_text.startswith("Earn $500")
    assert opp.metadata["platform"] == "WhatsApp"
    assert opp.processing_status == ProcessingStatus.NORMALIZED


def test_opportunity_input_image_creation():
    """Verify OpportunityInput creation with valid image data."""
    opp = OpportunityInput(
        source_type=SourceType.IMAGE,
        original_filename="whatsapp_offer.png",
        mime_type="image/png",
        raw_text=None,
        extracted_text="OCR Extracted: Remote Data Entry Internship Urgent",
        metadata={"byte_size": 102400},
        processing_status=ProcessingStatus.EXTRACTED,
    )
    assert opp.source_type == SourceType.IMAGE
    assert opp.source_type.value == "image"
    assert opp.original_filename == "whatsapp_offer.png"
    assert opp.mime_type == "image/png"
    assert opp.processing_status == ProcessingStatus.EXTRACTED


def test_opportunity_input_pdf_creation():
    """Verify OpportunityInput creation with valid PDF data."""
    opp = OpportunityInput(
        source_type=SourceType.PDF,
        original_filename="offer_letter.pdf",
        mime_type="application/pdf",
        raw_text=None,
        extracted_text="PDF Extracted: Official Offer Letter and Bank Deposit Requirement",
        metadata={"byte_size": 204800},
        processing_status=ProcessingStatus.EXTRACTED,
    )
    assert opp.source_type == SourceType.PDF
    assert opp.source_type.value == "pdf"
    assert opp.original_filename == "offer_letter.pdf"
    assert opp.mime_type == "application/pdf"


def test_opportunity_input_rejects_invalid_source_type():
    """Verify that unsupported source types raise validation error."""
    with pytest.raises(ValidationError):
        OpportunityInput(
            source_type="unsupported_source_type",  # type: ignore
            extracted_text="Some text",
        )


def test_opportunity_input_rejects_missing_required_fields():
    """Verify that missing extracted_text or source_type raises validation error."""
    with pytest.raises(ValidationError):
        OpportunityInput.model_validate({"source_type": "text"})  # missing extracted_text

    with pytest.raises(ValidationError):
        OpportunityInput.model_validate({"extracted_text": "hello"})  # missing source_type


# ----------------------------------------------------------------------
# 3. Processor Contracts and Implementation Tests
# ----------------------------------------------------------------------

def test_processor_hierarchy_and_contracts():
    """Verify all processors inherit from BaseInputProcessor and implement the interface."""
    assert issubclass(TextProcessor, BaseInputProcessor)
    assert issubclass(ImageProcessor, BaseInputProcessor)
    assert issubclass(PdfProcessor, BaseInputProcessor)


def test_text_processor_normalization():
    """Verify TextProcessor trims whitespace, standardizes line endings, and normalizes."""
    processor = TextProcessor()
    raw = "   \r\n\r\nUrgent Job Offer:   Data Entry Assistant  \n\n\n\nContact via Telegram.   \x00\r\n"
    result = processor.process(content=raw, metadata={"channel": "Telegram"})

    assert isinstance(result, OpportunityInput)
    assert result.source_type == SourceType.TEXT
    assert "\x00" not in result.extracted_text
    assert "\r" not in result.extracted_text
    assert result.extracted_text.startswith("Urgent Job Offer")
    assert result.extracted_text.endswith("Contact via Telegram.")
    assert result.metadata["channel"] == "Telegram"
    assert result.metadata["char_count"] > 0
    assert result.metadata["word_count"] > 0


def test_text_processor_validation_empty():
    """Verify TextProcessor rejects empty or whitespace-only strings."""
    processor = TextProcessor()
    with pytest.raises(ValueError, match="cannot be empty"):
        processor.process(content="   \n\t   ")


def test_image_processor_validation_and_structure():
    """Verify ImageProcessor validates file extension, mime types, and returns valid OpportunityInput."""
    processor = ImageProcessor()
    dummy_bytes = b"\x89PNG\r\n\x1a\n" + b"dummy image payload content"

    result = processor.process(
        content=dummy_bytes,
        filename="screenshot.png",
        mime_type="image/png",
        metadata={"user_device": "mobile"},
    )
    assert isinstance(result, OpportunityInput)
    assert result.source_type == SourceType.IMAGE
    assert result.original_filename == "screenshot.png"
    assert result.mime_type == "image/png"
    assert result.metadata["byte_size"] == len(dummy_bytes)
    assert result.metadata["ocr_status"] == "planned_placeholder"
    assert "PLANNED_OCR_EXTRACTION" in result.extracted_text


def test_image_processor_rejects_invalid_extension():
    """Verify ImageProcessor rejects dangerous or unsupported extensions (e.g. .exe)."""
    processor = ImageProcessor()
    dummy_bytes = b"fake payload"
    with pytest.raises(ValueError, match="Unsupported image extension"):
        processor.process(content=dummy_bytes, filename="malicious.exe", mime_type="image/png")


def test_image_processor_rejects_empty_file():
    """Verify ImageProcessor rejects 0-byte file."""
    processor = ImageProcessor()
    with pytest.raises(ValueError, match="empty"):
        processor.process(content=b"", filename="empty.jpg", mime_type="image/jpeg")


def test_pdf_processor_validation_and_structure():
    """Verify PdfProcessor validates PDF extension, mime types, and returns valid OpportunityInput."""
    processor = PdfProcessor()
    dummy_pdf_bytes = b"%PDF-1.4 dummy pdf header and payload"

    result = processor.process(
        content=dummy_pdf_bytes,
        filename="internship_offer.pdf",
        mime_type="application/pdf",
    )
    assert isinstance(result, OpportunityInput)
    assert result.source_type == SourceType.PDF
    assert result.original_filename == "internship_offer.pdf"
    assert result.mime_type == "application/pdf"
    assert result.metadata["byte_size"] == len(dummy_pdf_bytes)
    assert result.metadata["pdf_extraction_status"] == "planned_placeholder"
    assert "PLANNED_PDF_EXTRACTION" in result.extracted_text


def test_pdf_processor_rejects_invalid_mime():
    """Verify PdfProcessor rejects invalid mime types."""
    processor = PdfProcessor()
    with pytest.raises(ValueError, match="Unsupported PDF MIME type"):
        processor.process(
            content=b"%PDF-1.4...",
            filename="document.pdf",
            mime_type="application/x-executable",
        )


# ----------------------------------------------------------------------
# 4. InputService Orchestration Tests
# ----------------------------------------------------------------------

def test_input_service_text_orchestration():
    """Verify InputService properly routes and processes plain text."""
    service = InputService()
    text = "Apply for Google Summer Internship by paying $100 processing fee."
    opp = service.process_text(text=text, metadata={"source": "SMS"})

    assert isinstance(opp, OpportunityInput)
    assert opp.source_type == SourceType.TEXT
    assert opp.extracted_text == text
    assert opp.metadata["source"] == "SMS"


def test_input_service_file_detection_and_routing():
    """Verify InputService detects file types and routes to appropriate processors."""
    service = InputService()

    # Route Image
    img_opp = service.process_file(
        content=b"dummy image bytes",
        filename="flyer.jpg",
        mime_type="image/jpeg",
    )
    assert img_opp.source_type == SourceType.IMAGE
    assert img_opp.original_filename == "flyer.jpg"

    # Route PDF
    pdf_opp = service.process_file(
        content=b"%PDF-1.5 test",
        filename="agreement.pdf",
        mime_type="application/pdf",
    )
    assert pdf_opp.source_type == SourceType.PDF
    assert pdf_opp.original_filename == "agreement.pdf"


def test_input_service_rejects_unsupported_file():
    """Verify InputService raises ValueError on unsupported file type (e.g. .docx or .sh)."""
    service = InputService()
    with pytest.raises(ValueError, match="Unsupported file format"):
        service.process_file(
            content=b"binary docx",
            filename="document.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


# ----------------------------------------------------------------------
# 5. API Route Intake Tests
# ----------------------------------------------------------------------

def test_api_analyze_text_endpoint(client: TestClient):
    """Verify POST /api/analyze/text receives request, normalizes, and responds."""
    payload = {
        "text": "Work from home part-time. Earn $50/hr. Deposit $20 for training materials.",
        "metadata": {"channel": "WhatsApp"},
    }
    response = client.post("/api/analyze/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_input"]["source_type"] == "text"
    assert data["normalized_input"]["extracted_text"].startswith("Work from home")
    assert data["normalized_input"]["metadata"]["channel"] == "WhatsApp"


def test_api_analyze_text_endpoint_validation_error(client: TestClient):
    """Verify POST /api/analyze/text rejects empty text with 422."""
    payload = {"text": "   "}
    response = client.post("/api/analyze/text", json=payload)
    assert response.status_code == 422


def test_api_analyze_file_endpoint_image(client: TestClient):
    """Verify POST /api/analyze/file processes uploaded image."""
    file_content = b"\x89PNG\r\n\x1a\nfakeimagecontent"
    files = {"file": ("screenshot.png", io.BytesIO(file_content), "image/png")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_input"]["source_type"] == "image"
    assert data["normalized_input"]["original_filename"] == "screenshot.png"


def test_api_analyze_file_endpoint_pdf(client: TestClient):
    """Verify POST /api/analyze/file processes uploaded PDF."""
    file_content = b"%PDF-1.4 test document stream"
    files = {"file": ("job_offer.pdf", io.BytesIO(file_content), "application/pdf")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["normalized_input"]["source_type"] == "pdf"
    assert data["normalized_input"]["original_filename"] == "job_offer.pdf"


def test_api_analyze_file_endpoint_unsupported(client: TestClient):
    """Verify POST /api/analyze/file rejects unsupported files with 422."""
    files = {"file": ("script.sh", io.BytesIO(b"#!/bin/bash\necho hello"), "application/x-sh")}
    response = client.post("/api/analyze/file", files=files)
    assert response.status_code == 422
