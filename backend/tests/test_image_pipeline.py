"""Comprehensive tests for the ScamCheck Image & OCR Pipeline.

Part 3 Verification:
- Validates image submissions across PNG, JPEG, and WEBP formats
- Tests local RapidOCR extraction on in-memory programmatically drawn images
- Verifies OCR text passes through TextProcessor for conservative normalization
- Confirms preservation of evidence markers: URLs, emails, phones, currencies,
  percentages, dates, and urgency punctuation
- Tests edge cases: blank images, corrupted images, oversized images, empty uploads
- Verifies API intake via multipart/form-data on POST /api/analyze/file
"""

import io
import pytest
from PIL import Image, ImageDraw, ImageFont
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.processors.image_processor import ImageProcessor
from backend.app.processors.text_processor import TextProcessor
from backend.app.schemas.opportunity import (
    OpportunityInput,
    ProcessingStatus,
    SourceType,
)
from backend.app.services.input_service import InputService
from backend.app.services.ocr_service import OCRResult, OCRService


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


def _generate_test_image(
    lines: list[str],
    img_format: str = "PNG",
    width: int = 600,
    line_height: int = 40,
    bg_color: tuple = (255, 255, 255),
    text_color: tuple = (0, 0, 0),
) -> bytes:
    """Helper to programmatically generate an image with clear text for OCR testing."""
    height = max(100, (len(lines) + 1) * line_height)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    y = 20
    for line in lines:
        draw.text((25, y), line, fill=text_color)
        y += line_height

    buf = io.BytesIO()
    img.save(buf, format=img_format)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. OCR Service Direct Unit Tests
# -----------------------------------------------------------------------------

def test_ocr_service_decodes_and_extracts_text():
    """Verify OCRService decodes a valid image and performs local OCR inference."""
    ocr_service = OCRService()
    img_bytes = _generate_test_image(["Junior Python Intern", "Stipend: $600/month"])

    result: OCRResult = ocr_service.extract_text_from_bytes(img_bytes)

    assert result.success is True
    assert result.engine == "RapidOCR-ONNX"
    assert result.image_width == 600
    assert result.image_height > 0
    assert result.line_count >= 1
    assert "Python" in result.text or "Intern" in result.text
    if result.confidence_avg is not None:
        assert 0.0 <= result.confidence_avg <= 1.0


def test_ocr_service_blank_image_returns_graceful_failure():
    """Verify OCRService on a blank image with no text returns success=False without raising error."""
    ocr_service = OCRService()
    blank_img = Image.new("RGB", (300, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    blank_img.save(buf, format="PNG")

    result: OCRResult = ocr_service.extract_text_from_bytes(buf.getvalue())

    assert result.success is False
    assert result.text == ""
    assert result.line_count == 0
    assert result.confidence_avg is None


def test_ocr_service_corrupted_image_raises_value_error():
    """Verify OCRService on corrupted/truncated image bytes raises ValueError."""
    ocr_service = OCRService()
    corrupted_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"random_corrupted_garbage"

    with pytest.raises(ValueError, match="corrupted or cannot be decoded"):
        ocr_service.extract_text_from_bytes(corrupted_bytes)


# -----------------------------------------------------------------------------
# 2. ImageProcessor Pipeline & Format Support Tests
# -----------------------------------------------------------------------------

def test_image_processor_png_format():
    """Verify ImageProcessor correctly processes PNG format images."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image(["Remote Frontend Internship", "Apply Now"], img_format="PNG")

    opp = processor.process(
        content=img_bytes,
        filename="job_posting.png",
        mime_type="image/png",
    )

    assert isinstance(opp, OpportunityInput)
    assert opp.source_type == SourceType.IMAGE
    assert opp.original_filename == "job_posting.png"
    assert opp.mime_type == "image/png"
    assert opp.processing_status == ProcessingStatus.NORMALIZED
    assert opp.metadata["ocr_engine"] == "RapidOCR-ONNX"
    assert opp.metadata["ocr_status"] == "success"
    assert opp.metadata["byte_size"] == len(img_bytes)
    assert len(opp.extracted_text) > 0


def test_image_processor_jpeg_format():
    """Verify ImageProcessor correctly processes JPEG format images."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image(["Data Analyst Role", "Salary: 45,000"], img_format="JPEG")

    opp = processor.process(
        content=img_bytes,
        filename="flyer.jpg",
        mime_type="image/jpeg",
    )

    assert opp.source_type == SourceType.IMAGE
    assert opp.original_filename == "flyer.jpg"
    assert opp.processing_status == ProcessingStatus.NORMALIZED
    assert len(opp.extracted_text) > 0


def test_image_processor_webp_format():
    """Verify ImageProcessor correctly processes WEBP format images."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image(["Campus Ambassador Program", "Earn Rewards"], img_format="WEBP")

    opp = processor.process(
        content=img_bytes,
        filename="screenshot.webp",
        mime_type="image/webp",
    )

    assert opp.source_type == SourceType.IMAGE
    assert opp.original_filename == "screenshot.webp"
    assert opp.processing_status == ProcessingStatus.NORMALIZED
    assert len(opp.extracted_text) > 0


def test_image_processor_blank_image_handling():
    """Verify ImageProcessor handles blank image without crashing, setting FAILED status."""
    processor = ImageProcessor()
    blank_img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    blank_img.save(buf, format="PNG")

    opp = processor.process(
        content=buf.getvalue(),
        filename="blank_screenshot.png",
        mime_type="image/png",
    )

    assert opp.source_type == SourceType.IMAGE
    assert opp.processing_status == ProcessingStatus.FAILED
    assert "OCR_NO_TEXT_DETECTED" in opp.extracted_text
    assert opp.metadata["ocr_status"] == "no_text_detected"


# -----------------------------------------------------------------------------
# 3. Evidence Extraction & Preservation through OCR
# -----------------------------------------------------------------------------

def test_ocr_preserves_urls():
    """Verify OCR extracts and preserves URLs from image screenshots."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "Apply at https://careers.example.com",
        "Official portal for students",
    ])
    opp = processor.process(content=img_bytes, filename="url_test.png")

    assert "https://careers.example.com" in opp.extracted_text or "example.com" in opp.extracted_text


def test_ocr_preserves_emails():
    """Verify OCR extracts and preserves email contact details."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "Send resume to recruiter@techcorp.io",
        "Subject: Summer Internship 2026",
    ])
    opp = processor.process(content=img_bytes, filename="email_test.png")

    assert "recruiter@techcorp.io" in opp.extracted_text or "techcorp.io" in opp.extracted_text


def test_ocr_preserves_phone_numbers():
    """Verify OCR extracts phone numbers."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "WhatsApp HR: +91 9876543210",
        "Urgent recruitment contact",
    ])
    opp = processor.process(content=img_bytes, filename="phone_test.png")

    assert "9876543210" in opp.extracted_text


def test_ocr_preserves_currency_and_amounts():
    """Verify OCR extracts monetary values and currency figures."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "Earn $500 Weekly",
        "Registration fee: Rs 2999",
    ])
    opp = processor.process(content=img_bytes, filename="currency_test.png")

    assert "500" in opp.extracted_text
    assert "2999" in opp.extracted_text


def test_ocr_preserves_percentages_and_numbers():
    """Verify OCR extracts percentages and numbers."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "Earn 40% Commission Daily",
        "Complete 20 Tasks per day",
    ])
    opp = processor.process(content=img_bytes, filename="numbers_test.png")

    assert "40%" in opp.extracted_text or "40" in opp.extracted_text
    assert "20" in opp.extracted_text


def test_ocr_preserves_dates():
    """Verify OCR extracts deadlines and dates."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "Application Deadline: 25/10/2026",
        "Start Date: November 2026",
    ])
    opp = processor.process(content=img_bytes, filename="dates_test.png")

    assert "2026" in opp.extracted_text


def test_ocr_preserves_urgency_punctuation_and_casing():
    """Verify OCR extracts uppercase urgency cues and exclamation marks."""
    processor = ImageProcessor()
    img_bytes = _generate_test_image([
        "URGENT HIRING: PAY TODAY!",
        "LIMITED SLOTS AVAILABLE!",
    ])
    opp = processor.process(content=img_bytes, filename="urgency_test.png")

    assert "URGENT" in opp.extracted_text or "HIRING" in opp.extracted_text
    assert "!" in opp.extracted_text or "PAY" in opp.extracted_text


# -----------------------------------------------------------------------------
# 4. Security, Validation & Error Handling
# -----------------------------------------------------------------------------

def test_image_processor_rejects_empty_file():
    """Verify ImageProcessor rejects 0-byte file with clean ValueError."""
    processor = ImageProcessor()
    with pytest.raises(ValueError, match="empty"):
        processor.process(content=b"", filename="empty.png", mime_type="image/png")


def test_image_processor_rejects_oversized_file():
    """Verify ImageProcessor rejects image exceeding 10 MB limit."""
    processor = ImageProcessor()
    oversized = b"0" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="exceeds the limit"):
        processor.process(content=oversized, filename="huge.jpg", mime_type="image/jpeg")


def test_image_processor_rejects_unsupported_extension():
    """Verify ImageProcessor rejects unsupported extensions (.gif, .exe, .bat)."""
    processor = ImageProcessor()
    dummy = _generate_test_image(["Test"])
    with pytest.raises(ValueError, match="Unsupported image extension"):
        processor.process(content=dummy, filename="animated.gif", mime_type="image/gif")


def test_image_processor_rejects_unsupported_mime():
    """Verify ImageProcessor rejects unsupported MIME types."""
    processor = ImageProcessor()
    dummy = _generate_test_image(["Test"])
    with pytest.raises(ValueError, match="Unsupported image MIME type"):
        processor.process(content=dummy, filename="image.png", mime_type="application/octet-stream")


def test_image_processor_rejects_corrupted_image_bytes():
    """Verify ImageProcessor raises clean ValueError on corrupt binary data."""
    processor = ImageProcessor()
    corrupt = b"\x89PNG\r\n\x1a\ncorrupted_payload_data_not_an_image"
    with pytest.raises(ValueError, match="corrupted or cannot be decoded"):
        processor.process(content=corrupt, filename="corrupt.png", mime_type="image/png")


# -----------------------------------------------------------------------------
# 5. Integration with InputService & TextProcessor
# -----------------------------------------------------------------------------

def test_input_service_routes_image_to_ocr_and_text_processor():
    """Verify InputService takes image bytes, runs OCR, and normalizes through TextProcessor."""
    service = InputService()
    img_bytes = _generate_test_image([
        "Full Stack Developer Internship",
        "Stipend: $1,200/month",
        "Apply at https://example.com",
    ])

    opp = service.process_file(
        content=img_bytes,
        filename="internship_ad.png",
        mime_type="image/png",
        metadata={"platform": "LinkedIn"},
    )

    assert isinstance(opp, OpportunityInput)
    assert opp.source_type == SourceType.IMAGE
    assert opp.original_filename == "internship_ad.png"
    assert opp.metadata["platform"] == "LinkedIn"
    assert opp.metadata["ocr_engine"] == "RapidOCR-ONNX"
    assert opp.metadata["char_count"] > 0
    assert opp.metadata["word_count"] > 0
    assert opp.processing_status == ProcessingStatus.NORMALIZED


# -----------------------------------------------------------------------------
# 6. REST API Endpoint (/api/analyze/file) Image Upload Tests
# -----------------------------------------------------------------------------

def test_api_analyze_file_image_success(client: TestClient):
    """Verify POST /api/analyze/file uploads image, runs OCR, and returns normalized OpportunityInput."""
    img_bytes = _generate_test_image([
        "Remote Content Writer Internship",
        "Compensation: $400/month",
        "Contact: hr@contentco.com",
    ])

    files = {"file": ("screenshot.png", io.BytesIO(img_bytes), "image/png")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "screenshot.png" in data["message"]

    norm = data["normalized_input"]
    assert norm["source_type"] == "image"
    assert norm["original_filename"] == "screenshot.png"
    assert norm["mime_type"] == "image/png"
    assert norm["metadata"]["ocr_engine"] == "RapidOCR-ONNX"
    assert norm["metadata"]["ocr_status"] == "success"
    assert len(norm["extracted_text"]) > 0


def test_api_analyze_file_corrupted_image(client: TestClient):
    """Verify POST /api/analyze/file returns clean 422 JSON error without stack trace on corrupt image."""
    corrupt_bytes = b"\x89PNG\r\n\x1a\ncorrupt_bytes_stream"
    files = {"file": ("corrupt.png", io.BytesIO(corrupt_bytes), "image/png")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "corrupted" in data["detail"]
    assert "Traceback" not in response.text


def test_api_analyze_file_unsupported_extension(client: TestClient):
    """Verify POST /api/analyze/file rejects unsupported extensions with clean 422 error."""
    files = {"file": ("malicious.exe", io.BytesIO(b"binary exe"), "application/x-msdownload")}
    response = client.post("/api/analyze/file", files=files)

    assert response.status_code == 422
    assert "Traceback" not in response.text
