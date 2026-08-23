"""Comprehensive tests for the ScamCheck Text Input Pipeline.

Part 2 Verification:
- Validates direct text inputs across diverse real-world student opportunity types
- Verifies rejection of empty, whitespace-only, and oversized text inputs
- Confirms 100% preservation of evidence markers: URLs, emails, phones, currencies,
  percentages, dates, punctuation, casing, emojis, and unicode
- Tests multiline and paragraph structure preservation
- Verifies API endpoint intake, clean error handling without tracebacks, and security
"""

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.processors.text_processor import TextProcessor
from backend.app.schemas.opportunity import (
    OpportunityInput,
    ProcessingStatus,
    SourceType,
    TextSubmissionRequest,
)
from backend.app.services.input_service import InputService


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Basic & Boundary Text Inputs
# -----------------------------------------------------------------------------

def test_normal_valid_text():
    """Verify normal valid opportunity description passes processing."""
    processor = TextProcessor()
    text = (
        "We are looking for a remote Graphic Design intern. "
        "Duration: 2 months. Stipend: $500/month."
    )
    result = processor.process(content=text)

    assert isinstance(result, OpportunityInput)
    assert result.source_type == SourceType.TEXT
    assert result.raw_text == text
    assert result.extracted_text == text
    assert result.processing_status == ProcessingStatus.NORMALIZED
    assert result.metadata["word_count"] > 0
    assert result.metadata["char_count"] == len(text)
    assert result.metadata["line_count"] == 1


def test_very_short_valid_text():
    """Verify very short single-sentence text is accepted."""
    processor = TextProcessor()
    text = "Hiring interns now."
    result = processor.process(content=text)
    assert result.extracted_text == "Hiring interns now."
    assert result.metadata["word_count"] == 3


def test_long_valid_text():
    """Verify a substantial multi-paragraph job description is accepted and normalized."""
    processor = TextProcessor()
    paragraphs = [
        "Position: Full Stack Engineering Intern",
        "About the Role: Work with our engineering team on modern web platforms.",
        "Requirements:\n- Python and JavaScript\n- Eager to learn\n- Strong communication",
        "Perks:\n- Flexible hours\n- Mentorship program\n- Certificate of completion",
        "Compensation: ₹25,000 per month stipend.",
    ]
    long_text = "\n\n".join(paragraphs)
    result = processor.process(content=long_text)

    assert result.extracted_text.startswith("Position: Full Stack")
    assert result.extracted_text.endswith("per month stipend.")
    assert result.metadata["word_count"] >= 30
    assert result.metadata["line_count"] >= 8


def test_empty_string_rejection():
    """Verify empty string raises a clean ValueError."""
    processor = TextProcessor()
    with pytest.raises(ValueError, match="cannot be empty or whitespace only"):
        processor.process(content="")


def test_whitespace_only_string_rejection():
    """Verify whitespace-only string raises a clean ValueError."""
    processor = TextProcessor()
    with pytest.raises(ValueError, match="cannot be empty or whitespace only"):
        processor.process(content="   \n\t  \r\n   ")


def test_non_string_type_rejection():
    """Verify non-string input raises a clean ValueError."""
    processor = TextProcessor()
    with pytest.raises(ValueError, match="Input text must be a string"):
        processor.process(content=12345)  # type: ignore


def test_oversized_text_rejection():
    """Verify oversized text exceeding max limit is rejected with informative error."""
    processor = TextProcessor(max_text_length=500)
    oversized_text = "A" * 501

    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        processor.process(content=oversized_text)


# -----------------------------------------------------------------------------
# 2. Critical Evidence Preservation Tests
# -----------------------------------------------------------------------------

def test_evidence_preservation_urls():
    """Verify URLs (http, https, domain routes, query params) are 100% preserved."""
    processor = TextProcessor()
    text = (
        "Apply at https://careers.example.com/internships?ref=whatsapp#apply "
        "or visit http://bit.ly/quick-intern-2026."
    )
    result = processor.process(content=text)
    assert "https://careers.example.com/internships?ref=whatsapp#apply" in result.extracted_text
    assert "http://bit.ly/quick-intern-2026" in result.extracted_text


def test_evidence_preservation_emails():
    """Verify email addresses with varied formats are preserved."""
    processor = TextProcessor()
    text = "Send resume to recruiter@tech-startup.io and cc hr.dept@global-corp.co.in."
    result = processor.process(content=text)
    assert "recruiter@tech-startup.io" in result.extracted_text
    assert "hr.dept@global-corp.co.in" in result.extracted_text


def test_evidence_preservation_phone_numbers():
    """Verify phone numbers with country codes, spaces, and brackets are preserved."""
    processor = TextProcessor()
    text = "Call +91 9876543210 or WhatsApp +1 (555) 234-5678 immediately."
    result = processor.process(content=text)
    assert "+91 9876543210" in result.extracted_text
    assert "+1 (555) 234-5678" in result.extracted_text


def test_evidence_preservation_currencies():
    """Verify currency symbols (₹, $, €, £, ¥) and amounts are preserved."""
    processor = TextProcessor()
    text = (
        "Registration fee: ₹2,999. First payout: $500 USD (€450 / £380). "
        "Security deposit: ¥50,000."
    )
    result = processor.process(content=text)
    assert "₹2,999" in result.extracted_text
    assert "$500" in result.extracted_text
    assert "€450" in result.extracted_text
    assert "£380" in result.extracted_text
    assert "¥50,000" in result.extracted_text


def test_evidence_preservation_numbers_and_percentages():
    """Verify numerical values, percentages, and metrics are preserved."""
    processor = TextProcessor()
    text = "Earn 40% daily commission on 15 completed micro-tasks."
    result = processor.process(content=text)
    assert "40%" in result.extracted_text
    assert "15" in result.extracted_text


def test_evidence_preservation_dates():
    """Verify dates in various formats are preserved."""
    processor = TextProcessor()
    text = "Deadline: 25/10/2026. Training starts on November 1st, 2026 (2026-11-01)."
    result = processor.process(content=text)
    assert "25/10/2026" in result.extracted_text
    assert "November 1st, 2026" in result.extracted_text
    assert "2026-11-01" in result.extracted_text


def test_evidence_preservation_punctuation_and_casing():
    """Verify urgent punctuation and uppercase emphasis are strictly preserved."""
    processor = TextProcessor()
    text = "URGENT HIRING: PAY ₹5,000 TODAY!!! DO NOT MISS OUT!!!"
    result = processor.process(content=text)
    assert "URGENT HIRING: PAY ₹5,000 TODAY!!! DO NOT MISS OUT!!!" == result.extracted_text


def test_evidence_preservation_emojis():
    """Verify emojis frequently used in scam & marketing lures are preserved."""
    processor = TextProcessor()
    text = "🎉 Congratulations! 💰 Earn ₹5,000/day 🚀 Work from Home ⚠️ Limited Slots!"
    result = processor.process(content=text)
    assert "🎉" in result.extracted_text
    assert "💰" in result.extracted_text
    assert "🚀" in result.extracted_text
    assert "⚠️" in result.extracted_text


def test_multilingual_unicode_support():
    """Verify non-English and accented Unicode scripts are handled without encoding faults."""
    processor = TextProcessor()
    text = (
        "Offre de stage à Paris: Rémunération 800€/mois. "
        "सॉफ्टवेयर इंटर्नशिप: ₹15,000 प्रति माह। "
        "实习机会：每月5000元。"
    )
    result = processor.process(content=text)
    assert "Rémunération 800€/mois" in result.extracted_text
    assert "सॉफ्टवेयर इंटर्नशिप: ₹15,000 प्रति माह।" in result.extracted_text
    assert "实习机会：每月5000元。" in result.extracted_text


# -----------------------------------------------------------------------------
# 3. Formatting, Paragraph, and Control Character Normalization
# -----------------------------------------------------------------------------

def test_multiline_paragraph_structure_preservation():
    """Verify realistic multi-paragraph opportunity preserves readable paragraph structure."""
    processor = TextProcessor()
    raw = (
        "Congratulations!\n\n"
        "You have been selected for our remote data internship program.\n\n"
        "Duration: 3 months\n"
        "Stipend: ₹15,000/month\n\n"
        "Contact:\n"
        "recruiter@example.com\n\n"
        "Apply here:\n"
        "https://example.com/apply"
    )
    result = processor.process(content=raw)
    assert result.extracted_text == raw
    assert result.metadata["line_count"] == len(raw.splitlines())


def test_line_ending_standardization():
    """Verify mixed CRLF (Windows) and CR (Classic Mac) line endings are standardized to LF."""
    processor = TextProcessor()
    raw = "Line 1\r\nLine 2\rLine 3\nLine 4"
    result = processor.process(content=raw)
    assert result.extracted_text == "Line 1\nLine 2\nLine 3\nLine 4"
    assert "\r" not in result.extracted_text


def test_excessive_blank_line_collapse():
    """Verify 4+ consecutive newlines are collapsed to 2 while keeping paragraph separation."""
    processor = TextProcessor()
    raw = "Header\n\n\n\n\n\nBody paragraph\n\n\n\nFooter"
    result = processor.process(content=raw)
    assert result.extracted_text == "Header\n\nBody paragraph\n\nFooter"


def test_dangerous_control_characters_removed():
    """Verify invisible control bytes (null bytes, bell, escape) are safely removed without altering text."""
    processor = TextProcessor()
    raw = "Legit \x00Job \x07Offer \x1bWith \x1fControl \x7fBytes"
    result = processor.process(content=raw)
    assert result.extracted_text == "Legit Job Offer With Control Bytes"


def test_raw_text_vs_extracted_text_integrity():
    """Verify raw_text stores pristine original input while extracted_text stores normalized content."""
    processor = TextProcessor()
    raw = "   \r\n  Job Offer: Data Entry \x00 \n\n\n\n Contact recruiter@co.in   "
    result = processor.process(content=raw)

    assert result.raw_text == raw  # Original untouched
    assert result.extracted_text == "Job Offer: Data Entry  \n\n Contact recruiter@co.in"
    assert result.extracted_text != raw


# -----------------------------------------------------------------------------
# 4. Security & Data Inertness
# -----------------------------------------------------------------------------

def test_security_text_treated_strictly_as_data():
    """Verify command injection, SQL, and script tags are treated strictly as inert string data."""
    processor = TextProcessor()
    dangerous_payload = (
        "rm -rf / && sudo reboot; "
        "<script>alert('xss')</script> "
        "'; DROP TABLE users; -- "
        "eval(import('os').system('calc'))"
    )
    result = processor.process(content=dangerous_payload)
    assert isinstance(result, OpportunityInput)
    assert result.extracted_text == dangerous_payload


# -----------------------------------------------------------------------------
# 5. InputService Text Orchestration
# -----------------------------------------------------------------------------

def test_input_service_custom_text_processor():
    """Verify InputService accepts and utilizes configured text processor instance."""
    custom_processor = TextProcessor(max_text_length=200)
    service = InputService(text_processor=custom_processor)

    # Valid within limit
    opp = service.process_text("Short valid opportunity", metadata={"source": "Telegram"})
    assert opp.source_type == SourceType.TEXT
    assert opp.metadata["source"] == "Telegram"

    # Reject exceeding limit
    with pytest.raises(ValueError, match="exceeds maximum allowed limit"):
        service.process_text("X" * 250)


# -----------------------------------------------------------------------------
# 6. REST API Endpoint Tests (/api/analyze/text)
# -----------------------------------------------------------------------------

def test_api_text_success_structured_response(client: TestClient):
    """Verify POST /api/analyze/text returns 200 with complete structured JSON."""
    payload = {
        "text": (
            "Congratulations! You have been selected for a remote software internship. "
            "Please pay ₹2,999 as a registration fee to confirm your position. "
            "Contact: recruiter@example.com | https://example.com"
        ),
        "metadata": {
            "channel": "WhatsApp",
            "sender_id": "+919876543210",
        },
    }
    response = client.post("/api/analyze/text", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Text opportunity normalized successfully."

    norm = data["normalized_input"]
    assert norm["source_type"] == "text"
    assert norm["processing_status"] == "normalized"
    assert "₹2,999" in norm["extracted_text"]
    assert "recruiter@example.com" in norm["extracted_text"]
    assert "https://example.com" in norm["extracted_text"]
    assert norm["metadata"]["channel"] == "WhatsApp"
    assert norm["metadata"]["sender_id"] == "+919876543210"
    assert norm["metadata"]["word_count"] > 10


def test_api_text_missing_text_field(client: TestClient):
    """Verify POST /api/analyze/text with missing 'text' field returns clean 422 JSON without stack traces."""
    response = client.post("/api/analyze/text", json={})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Ensure no python traceback is leaked
    assert "Traceback" not in response.text


def test_api_text_empty_string(client: TestClient):
    """Verify POST /api/analyze/text with empty string returns clean 422 JSON."""
    response = client.post("/api/analyze/text", json={"text": ""})
    assert response.status_code == 422
    assert "Traceback" not in response.text


def test_api_text_whitespace_only(client: TestClient):
    """Verify POST /api/analyze/text with whitespace-only string returns clean 422 JSON."""
    response = client.post("/api/analyze/text", json={"text": "   \n\t   "})
    assert response.status_code == 422
    assert "Traceback" not in response.text


def test_api_text_incorrect_data_type(client: TestClient):
    """Verify POST /api/analyze/text with non-string data type returns clean 422 JSON."""
    response = client.post("/api/analyze/text", json={"text": 98765})
    assert response.status_code == 422
    assert "Traceback" not in response.text


def test_api_text_oversized_payload(client: TestClient):
    """Verify POST /api/analyze/text with oversized input returns clean 422."""
    oversized = "A" * 100_001
    response = client.post("/api/analyze/text", json={"text": oversized})
    assert response.status_code == 422
    data = response.json()
    assert "exceeds maximum allowed limit" in data["detail"]
    assert "Traceback" not in response.text
