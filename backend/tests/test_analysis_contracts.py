"""Comprehensive tests for the ScamCheck Common Analysis Data Contracts.

Verification:
- Validates model instantiation across all analysis models and enums
- Checks boundary validation on scores, confidences, and enum values
- Validates missing required fields and optional field defaults
- Verifies nested structure serialization (AnalysisResult -> RiskSignal -> Evidence)
- Tests compatibility with OpportunityInput across all modalities (text, image, pdf)
- Tests JSON serialization and dictionary dump integrity
- Verifies non-binary risk representation (LOW, MEDIUM, HIGH, CRITICAL)
- Ensures failed analysis status is cleanly decoupled from risk signals
"""

import json
import pytest
from pydantic import ValidationError

from backend.app.analysis import (
    AnalysisContext,
    AnalysisResult,
    AnalysisStatus,
    ContactInfoEntity,
    DateEntity,
    EmailEntity,
    Evidence,
    ExtractedEntities,
    JobTitleEntity,
    LocationEntity,
    MonetaryAmountEntity,
    OrganizationEntity,
    PaymentDetailEntity,
    PercentageEntity,
    PhoneEntity,
    RiskLevel,
    RiskSignal,
    SignalSeverity,
    UrlEntity,
)
from backend.app.schemas.opportunity import (
    OpportunityInput,
    ProcessingStatus,
    SourceType,
)


# -----------------------------------------------------------------------------
# 1. Enums Testing
# -----------------------------------------------------------------------------

def test_risk_level_enum_values():
    """Verify RiskLevel contains only non-binary calibrated risk bands."""
    assert RiskLevel.LOW == "low"
    assert RiskLevel.MEDIUM == "medium"
    assert RiskLevel.HIGH == "high"
    assert RiskLevel.CRITICAL == "critical"
    
    # Ensure binary "SCAM" / "NOT_SCAM" are NOT valid enum members
    assert "scam" not in [r.value for r in RiskLevel]
    assert "not_scam" not in [r.value for r in RiskLevel]


def test_signal_severity_enum_values():
    """Verify SignalSeverity contains standard classification levels."""
    assert SignalSeverity.LOW == "low"
    assert SignalSeverity.MEDIUM == "medium"
    assert SignalSeverity.HIGH == "high"
    assert SignalSeverity.CRITICAL == "critical"


def test_analysis_status_enum_values():
    """Verify AnalysisStatus lifecycle enum values."""
    assert AnalysisStatus.NOT_STARTED == "not_started"
    assert AnalysisStatus.PROCESSING == "processing"
    assert AnalysisStatus.COMPLETED == "completed"
    assert AnalysisStatus.PARTIAL == "partial"
    assert AnalysisStatus.FAILED == "failed"


# -----------------------------------------------------------------------------
# 2. Evidence Model Tests
# -----------------------------------------------------------------------------

def test_evidence_model_valid_instantiation():
    """Verify Evidence model instantiation with required and optional fields."""
    ev = Evidence(
        type="payment_amount",
        value="₹999",
        source="text",
        location="line:2",
        context="Pay ₹999 registration fee immediately",
        normalized_value="999 INR",
        metadata={"currency": "INR", "numeric": 999},
    )

    assert ev.type == "payment_amount"
    assert ev.value == "₹999"
    assert ev.source == "text"
    assert ev.location == "line:2"
    assert ev.context == "Pay ₹999 registration fee immediately"
    assert ev.normalized_value == "999 INR"
    assert ev.metadata["numeric"] == 999


def test_evidence_model_missing_required_fields():
    """Verify Evidence requires type and value fields."""
    with pytest.raises(ValidationError):
        Evidence(type="payment_amount")  # missing value

    with pytest.raises(ValidationError):
        Evidence(value="₹999")  # missing type


def test_evidence_model_default_source():
    """Verify Evidence defaults source to 'text'."""
    ev = Evidence(type="urgency_phrase", value="immediately")
    assert ev.source == "text"
    assert ev.location is None
    assert ev.context is None
    assert ev.metadata == {}


# -----------------------------------------------------------------------------
# 3. Extracted Entity Models Tests
# -----------------------------------------------------------------------------

def test_individual_entity_models():
    """Verify construction and validation of each extracted entity model."""
    org = OrganizationEntity(name="Acme Corp", domain="acme.com", confidence=0.95)
    assert org.name == "Acme Corp"
    assert org.domain == "acme.com"
    assert org.confidence == 0.95

    job = JobTitleEntity(title="Software Engineer Intern", department="Engineering")
    assert job.title == "Software Engineer Intern"

    email = EmailEntity(email="recruiter@gmail.com", domain="gmail.com", is_free_provider=True)
    assert email.email == "recruiter@gmail.com"
    assert email.is_free_provider is True

    phone = PhoneEntity(number="+91 9876543210", country_code="+91", normalized_number="+919876543210")
    assert phone.number == "+91 9876543210"

    url = UrlEntity(url="https://bit.ly/fakejob", domain="bit.ly", is_shortened=True)
    assert url.is_shortened is True

    money = MonetaryAmountEntity(raw_amount="₹5,000", currency="INR", numeric_value=5000.0, purpose="fee")
    assert money.numeric_value == 5000.0
    assert money.purpose == "fee"

    pct = PercentageEntity(raw_percentage="30% commission", numeric_value=30.0)
    assert pct.numeric_value == 30.0

    dt = DateEntity(raw_date="25/10/2026", parsed_date="2026-10-25", date_type="deadline")
    assert dt.date_type == "deadline"

    loc = LocationEntity(raw_location="Remote (India)", is_remote=True)
    assert loc.is_remote is True

    pmt = PaymentDetailEntity(payment_type="registration_fee", amount="₹999", upi_id="pay@upi")
    assert pmt.upi_id == "pay@upi"

    contact = ContactInfoEntity(
        primary_channel="whatsapp",
        emails=["hr@company.com"],
        phone_numbers=["+919876543210"],
        social_handles={"telegram": "@hr_recruiter"},
    )
    assert contact.social_handles["telegram"] == "@hr_recruiter"


def test_extracted_entities_container():
    """Verify ExtractedEntities container aggregates all entities with defaults."""
    entities = ExtractedEntities()
    assert entities.organizations == []
    assert entities.job_titles == []
    assert entities.emails == []
    assert entities.phone_numbers == []
    assert entities.urls == []
    assert entities.monetary_amounts == []
    assert entities.percentages == []
    assert entities.dates == []
    assert entities.locations == []
    assert entities.payment_details == []
    assert entities.contact_info is None
    assert entities.raw_entities == {}


def test_extracted_entities_populated():
    """Verify ExtractedEntities holds populated entity collections."""
    entities = ExtractedEntities(
        organizations=[OrganizationEntity(name="Global Tech")],
        emails=[EmailEntity(email="hr@gmail.com", is_free_provider=True)],
        monetary_amounts=[MonetaryAmountEntity(raw_amount="₹999", purpose="fee")],
    )
    assert len(entities.organizations) == 1
    assert entities.organizations[0].name == "Global Tech"
    assert len(entities.emails) == 1
    assert len(entities.monetary_amounts) == 1


# -----------------------------------------------------------------------------
# 4. RiskSignal Model Tests
# -----------------------------------------------------------------------------

def test_risk_signal_valid_instantiation():
    """Verify RiskSignal instantiation with full fields and nested evidence."""
    ev = Evidence(type="payment_amount", value="₹999", source="text")
    signal = RiskSignal(
        signal_id="SIG_UPFRONT_FEE",
        signal_type="financial_risk",
        title="Upfront Registration Fee",
        description="The opportunity asks for ₹999 before onboarding.",
        severity=SignalSeverity.HIGH,
        confidence=0.95,
        evidence=[ev],
        score_contribution=40.0,
        source="text_rule",
        explanation="Legitimate companies do not charge candidates fees.",
        metadata={"rule_id": "R_PAY_001"},
    )

    assert signal.signal_id == "SIG_UPFRONT_FEE"
    assert signal.signal_type == "financial_risk"
    assert signal.severity == SignalSeverity.HIGH
    assert signal.confidence == 0.95
    assert len(signal.evidence) == 1
    assert signal.evidence[0].value == "₹999"
    assert signal.score_contribution == 40.0
    assert signal.source == "text_rule"


def test_risk_signal_confidence_bounds():
    """Verify RiskSignal confidence must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        RiskSignal(
            signal_id="SIG_TEST",
            signal_type="test",
            title="Test",
            description="Test",
            severity=SignalSeverity.LOW,
            confidence=1.5,  # Invalid: > 1.0
        )

    with pytest.raises(ValidationError):
        RiskSignal(
            signal_id="SIG_TEST",
            signal_type="test",
            title="Test",
            description="Test",
            severity=SignalSeverity.LOW,
            confidence=-0.1,  # Invalid: < 0.0
        )


def test_risk_signal_score_contribution_bounds():
    """Verify RiskSignal score_contribution must be between 0.0 and 100.0."""
    with pytest.raises(ValidationError):
        RiskSignal(
            signal_id="SIG_TEST",
            signal_type="test",
            title="Test",
            description="Test",
            severity=SignalSeverity.LOW,
            score_contribution=105.0,  # Invalid: > 100.0
        )


def test_risk_signal_multi_source_support():
    """Verify RiskSignal can represent signals from OCR, PDF, ML, or URL analyzers."""
    sig_ocr = RiskSignal(
        signal_id="SIG_OCR_FEE",
        signal_type="financial_risk",
        title="Payment Mention in Screenshot",
        description="OCR detected payment request in flyer",
        severity=SignalSeverity.HIGH,
        source="ocr_extractor",
    )
    assert sig_ocr.source == "ocr_extractor"

    sig_ml = RiskSignal(
        signal_id="SIG_SEMANTIC_SCAM",
        signal_type="ml_classification",
        title="High Semantic Fraud Probability",
        description="ML model detected deceptive phrasing patterns",
        severity=SignalSeverity.CRITICAL,
        confidence=0.88,
        source="ml_classifier",
    )
    assert sig_ml.source == "ml_classifier"

    sig_url = RiskSignal(
        signal_id="SIG_LOOKALIKE_DOMAIN",
        signal_type="domain_analysis",
        title="Typosquatted Company Domain",
        description="Domain simulates a known corporate brand",
        severity=SignalSeverity.HIGH,
        source="url_analyzer",
    )
    assert sig_url.source == "url_analyzer"


# -----------------------------------------------------------------------------
# 5. AnalysisContext Model Tests
# -----------------------------------------------------------------------------

def test_analysis_context_instantiation():
    """Verify AnalysisContext correctly encapsulates OpportunityInput and analytical components."""
    opp = OpportunityInput(
        source_type=SourceType.TEXT,
        extracted_text="Work from home. Pay ₹999.",
        processing_status=ProcessingStatus.NORMALIZED,
    )

    ctx = AnalysisContext(
        opportunity=opp,
        source_metadata={"channel": "Telegram"},
        status=AnalysisStatus.PROCESSING,
    )

    assert ctx.opportunity.source_type == SourceType.TEXT
    assert ctx.status == AnalysisStatus.PROCESSING
    assert ctx.source_metadata["channel"] == "Telegram"
    assert ctx.extracted_entities.organizations == []
    assert ctx.evidence_pool == []
    assert ctx.error_message is None


# -----------------------------------------------------------------------------
# 6. AnalysisResult Model Tests
# -----------------------------------------------------------------------------

def test_analysis_result_valid_instantiation():
    """Verify AnalysisResult represents complete explainable risk assessment."""
    ev1 = Evidence(type="payment_amount", value="₹999", source="text")
    ev2 = Evidence(type="urgency_phrase", value="immediately", source="text")

    sig1 = RiskSignal(
        signal_id="SIG_UPFRONT_FEE",
        signal_type="financial_risk",
        title="Upfront Fee",
        description="Requires ₹999 payment.",
        severity=SignalSeverity.HIGH,
        evidence=[ev1],
        score_contribution=45.0,
    )
    sig2 = RiskSignal(
        signal_id="SIG_URGENT_CALL",
        signal_type="urgency_pressure",
        title="Urgent Call to Action",
        description="Demands immediate payment.",
        severity=SignalSeverity.MEDIUM,
        evidence=[ev2],
        score_contribution=20.0,
    )

    result = AnalysisResult(
        source_type=SourceType.TEXT,
        risk_score=65,
        risk_level=RiskLevel.HIGH,
        signals=[sig1, sig2],
        evidence=[ev1, ev2],
        summary="High risk detected due to upfront payment and pressure tactics.",
        reasons=[
            "Upfront registration fee requested",
            "Urgency language detected",
        ],
        status=AnalysisStatus.COMPLETED,
        analysis_metadata={"evaluator_version": "0.1.0"},
    )

    assert result.source_type == SourceType.TEXT
    assert result.risk_score == 65
    assert result.risk_level == RiskLevel.HIGH
    assert len(result.signals) == 2
    assert len(result.evidence) == 2
    assert len(result.reasons) == 2
    assert result.status == AnalysisStatus.COMPLETED


def test_analysis_result_risk_score_bounds():
    """Verify risk_score must be between 0 and 100 integer."""
    with pytest.raises(ValidationError):
        AnalysisResult(source_type=SourceType.TEXT, risk_score=105)  # > 100

    with pytest.raises(ValidationError):
        AnalysisResult(source_type=SourceType.TEXT, risk_score=-5)  # < 0


def test_analysis_result_empty_signals_and_low_risk():
    """Verify AnalysisResult handles benign opportunities with 0 signals cleanly."""
    result = AnalysisResult(
        source_type=SourceType.TEXT,
        risk_score=5,
        risk_level=RiskLevel.LOW,
        signals=[],
        evidence=[],
        reasons=["No suspicious risk indicators detected"],
        status=AnalysisStatus.COMPLETED,
    )

    assert result.risk_score == 5
    assert result.risk_level == RiskLevel.LOW
    assert result.signals == []
    assert result.evidence == []


def test_analysis_result_failed_status_decoupled_from_scam():
    """Verify AnalysisResult handles failed extraction without assigning high scam risk."""
    result = AnalysisResult(
        source_type=SourceType.IMAGE,
        risk_score=None,
        risk_level=RiskLevel.LOW,
        signals=[],
        summary="Image extraction failed due to unreadable content.",
        status=AnalysisStatus.FAILED,
        analysis_metadata={"error": "OCR_NO_TEXT_DETECTED"},
    )

    assert result.status == AnalysisStatus.FAILED
    assert result.risk_score is None
    assert result.signals == []


# -----------------------------------------------------------------------------
# 7. Serialization & JSON Compatibility Tests
# -----------------------------------------------------------------------------

def test_analysis_result_json_serialization_roundtrip():
    """Verify complete AnalysisResult can serialize to JSON and deserialize back losslessly."""
    ev = Evidence(type="url", value="https://fake-internships.xyz", source="pdf")
    sig = RiskSignal(
        signal_id="SIG_SUSP_URL",
        signal_type="domain_risk",
        title="Suspicious Application URL",
        description="Uses non-standard TLD",
        severity=SignalSeverity.HIGH,
        evidence=[ev],
    )
    original = AnalysisResult(
        source_type=SourceType.PDF,
        risk_score=70,
        risk_level=RiskLevel.HIGH,
        signals=[sig],
        evidence=[ev],
        reasons=["Suspicious top-level domain for company portal"],
        status=AnalysisStatus.COMPLETED,
    )

    # Serialize to JSON string
    json_str = original.model_dump_json()
    assert isinstance(json_str, str)

    # Parse JSON and recreate model
    parsed_dict = json.loads(json_str)
    recreated = AnalysisResult.model_validate(parsed_dict)

    assert recreated.source_type == SourceType.PDF
    assert recreated.risk_score == 70
    assert recreated.risk_level == RiskLevel.HIGH
    assert len(recreated.signals) == 1
    assert recreated.signals[0].signal_id == "SIG_SUSP_URL"
    assert recreated.signals[0].evidence[0].value == "https://fake-internships.xyz"


def test_analysis_context_with_opportunity_input_roundtrip():
    """Verify AnalysisContext serialization alongside OpportunityInput."""
    opp = OpportunityInput(
        source_type=SourceType.PDF,
        original_filename="offer_letter.pdf",
        mime_type="application/pdf",
        extracted_text="Pay ₹1,500 security deposit",
        processing_status=ProcessingStatus.NORMALIZED,
        metadata={"pdf_page_count": 1},
    )
    ctx = AnalysisContext(opportunity=opp, status=AnalysisStatus.PROCESSING)

    json_str = ctx.model_dump_json()
    parsed_dict = json.loads(json_str)
    recreated = AnalysisContext.model_validate(parsed_dict)

    assert recreated.opportunity.source_type == SourceType.PDF
    assert recreated.opportunity.original_filename == "offer_letter.pdf"
    assert recreated.opportunity.metadata["pdf_page_count"] == 1
