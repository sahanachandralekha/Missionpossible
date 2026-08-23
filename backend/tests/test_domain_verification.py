"""Unit and Integration Tests for ScamCheck External Domain Verification & Identity Intelligence.

STATUS: FULLY IMPLEMENTED (Part 12)

Verifies:
- Domain verification provider abstraction (Offline, Network, Mock)
- SSRF defenses (Blocking private IPs, loopback, link-local, cloud metadata, invalid schemes)
- Domain verification signal categories:
  - SIG_DOMAIN_UNRESOLVED
  - SIG_DOMAIN_REDIRECT_ANOMALY
  - SIG_DOMAIN_ORGANIZATION_INCONSISTENCY
  - SIG_DOMAIN_TLS_ANOMALY
  - SIG_DOMAIN_REGISTRATION_ANOMALY
  - SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE
- Traceable evidence construction without fabricated offsets
- Multimodal source modality preservation (Text, Image/OCR, PDF)
- Signal deduplication and evidence consolidation
- Complete offline invariant (zero socket/HTTP/DNS requests by default)
- Security and prompt-injection neutrality
- Technical provider failure isolation
- Risk scoring engine integration (RULE_WEIGHTS, score_contribution=0.0 from verifier)
- Full end-to-end integration with AnalysisService
"""

import socket
import pytest
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType
from backend.app.analysis.models import (
    AnalysisContext,
    AnalysisResult,
    AnalysisStatus,
    ExtractedEntities,
    OrganizationEntity,
    RiskLevel,
    RiskSignal,
    SignalSeverity,
    UrlEntity,
)
from backend.app.analysis.domain import (
    DNSResolutionStatus,
    DomainRegistrationInfo,
    DomainTLSInfo,
    DomainVerificationReport,
    DomainVerifier,
    HTTPReachabilityStatus,
    MockDomainVerificationProvider,
    NetworkDomainVerificationProvider,
    OfflineDomainVerificationProvider,
    get_domain_verification_provider,
)
from backend.app.analysis.domain.domain_rules import (
    is_hostname_restricted,
    is_ip_restricted,
)
from backend.app.analysis.risk import RiskScoringEngine
from backend.app.analysis import AnalysisService


@pytest.fixture
def verifier() -> DomainVerifier:
    return DomainVerifier(provider=OfflineDomainVerificationProvider())


def test_verifier_instantiates(verifier: DomainVerifier):
    """Verify DomainVerifier initializes cleanly with default offline provider."""
    assert verifier is not None
    assert verifier.get_provider_name() == "offline-fallback"


def test_empty_urls_returns_no_signals(verifier: DomainVerifier):
    """Verify empty URL list produces no signals safely."""
    assert verifier.verify_urls([]) == []


# -----------------------------------------------------------------------------
# SSRF & Security Defense Tests
# -----------------------------------------------------------------------------

def test_ssrf_private_and_restricted_ips_blocked():
    """Verify SSRF filters block private, loopback, link-local, and cloud metadata IPs."""
    # Loopback
    assert is_ip_restricted("127.0.0.1") is True
    assert is_ip_restricted("127.0.0.2") is True
    assert is_ip_restricted("::1") is True
    # Private RFC 1918
    assert is_ip_restricted("10.0.0.1") is True
    assert is_ip_restricted("172.16.5.10") is True
    assert is_ip_restricted("192.168.1.1") is True
    # Link-local / Cloud Metadata
    assert is_ip_restricted("169.254.169.254") is True
    assert is_ip_restricted("169.254.1.1") is True
    assert is_ip_restricted("fe80::1") is True
    # Public IPs (Allowed)
    assert is_ip_restricted("93.184.216.34") is False
    assert is_ip_restricted("8.8.8.8") is False
    assert is_ip_restricted("1.1.1.1") is False


def test_ssrf_restricted_hostnames_blocked():
    """Verify restricted hostnames are flagged and blocked."""
    assert is_hostname_restricted("localhost") is True
    assert is_hostname_restricted("127.0.0.1") is True
    assert is_hostname_restricted("0.0.0.0") is True
    assert is_hostname_restricted("metadata.google.internal") is True
    assert is_hostname_restricted("app.local") is True
    assert is_hostname_restricted("service.internal") is True
    assert is_hostname_restricted("192.168.1.1") is True
    # Public domain names (Allowed)
    assert is_hostname_restricted("google.com") is False
    assert is_hostname_restricted("careers.microsoft.com") is False


def test_ssrf_blocking_in_network_provider():
    """Verify NetworkDomainVerificationProvider blocks SSRF targets before connecting."""
    provider = NetworkDomainVerificationProvider()
    report_loopback = provider.verify("http://127.0.0.1:8080/admin")
    assert report_loopback.is_ssrf_blocked is True
    assert report_loopback.dns_status == DNSResolutionStatus.BLOCKED_SSRF

    report_metadata = provider.verify("http://169.254.169.254/latest/meta-data")
    assert report_metadata.is_ssrf_blocked is True


def test_invalid_scheme_rejected_by_network_provider():
    """Verify unsupported schemes (ftp, file, gopher) are rejected."""
    provider = NetworkDomainVerificationProvider()
    report = provider.verify("file:///etc/passwd")
    assert report.http_status == HTTPReachabilityStatus.INVALID_SCHEME


# -----------------------------------------------------------------------------
# Signal Categories Tests
# -----------------------------------------------------------------------------

def test_dns_unresolved_domain_signal():
    """Verify DNS failure generates SIG_DOMAIN_UNRESOLVED signal."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={"dns_status": DNSResolutionStatus.DOMAIN_DOES_NOT_RESOLVE}
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://non-existent-fake-careers-xyz987.com/apply")]
    signals = verifier.verify_urls(urls)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_UNRESOLVED" in signal_ids
    sig = next(s for s in signals if s.signal_id == "SIG_DOMAIN_UNRESOLVED")
    assert sig.severity == SignalSeverity.LOW
    assert sig.score_contribution == 0.0  # Scoring engine owns weights
    assert len(sig.evidence) == 1
    assert "fails DNS resolution" in sig.evidence[0].value


def test_cross_domain_redirect_anomaly_signal():
    """Verify cross-domain redirection triggers SIG_DOMAIN_REDIRECT_ANOMALY."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={
            "is_cross_domain_redirect": True,
            "final_url": "https://suspicious-different-destination.com/login",
            "redirect_count": 2,
        }
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://initial-portal.com/apply")]
    signals = verifier.verify_urls(urls)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_REDIRECT_ANOMALY" in signal_ids
    sig = next(s for s in signals if s.signal_id == "SIG_DOMAIN_REDIRECT_ANOMALY")
    assert sig.severity == SignalSeverity.MEDIUM


def test_https_downgrade_redirect_anomaly_signal():
    """Verify HTTPS -> HTTP downgrade redirection triggers SIG_DOMAIN_REDIRECT_ANOMALY."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={
            "is_https_downgrade": True,
            "final_url": "http://insecure-portal.com/login",
        }
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://secure-portal.com/apply")]
    signals = verifier.verify_urls(urls)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_REDIRECT_ANOMALY" in signal_ids


def test_organization_domain_inconsistency_signal():
    """Verify verified organization mismatch triggers SIG_DOMAIN_ORGANIZATION_INCONSISTENCY."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={"is_organization_consistent": False}
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://unrelated-third-party.com/jobs")]
    orgs = [OrganizationEntity(name="Apex Technologies")]
    signals = verifier.verify_urls(urls, claimed_organizations=orgs)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_ORGANIZATION_INCONSISTENCY" in signal_ids
    sig = next(s for s in signals if s.signal_id == "SIG_DOMAIN_ORGANIZATION_INCONSISTENCY")
    assert sig.severity == SignalSeverity.MEDIUM


def test_tls_anomaly_signal():
    """Verify TLS certificate failure triggers SIG_DOMAIN_TLS_ANOMALY."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={
            "tls": DomainTLSInfo(
                supports_https=False,
                certificate_valid=False,
                error="Self-signed certificate untrusted",
            )
        }
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://expired-ssl-careers.com/apply")]
    signals = verifier.verify_urls(urls)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_TLS_ANOMALY" in signal_ids
    sig = next(s for s in signals if s.signal_id == "SIG_DOMAIN_TLS_ANOMALY")
    assert sig.severity == SignalSeverity.LOW


def test_newly_registered_domain_anomaly_signal():
    """Verify newly registered domains trigger SIG_DOMAIN_REGISTRATION_ANOMALY."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={
            "registration": DomainRegistrationInfo(
                domain="fresh-careers-2026.com",
                is_newly_registered=True,
                age_days=6,
            )
        }
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://fresh-careers-2026.com/apply")]
    signals = verifier.verify_urls(urls)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_REGISTRATION_ANOMALY" in signal_ids
    sig = next(s for s in signals if s.signal_id == "SIG_DOMAIN_REGISTRATION_ANOMALY")
    assert sig.severity == SignalSeverity.MEDIUM


def test_infrastructure_unavailable_signal():
    """Verify 500 server errors trigger SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE without marking as critical."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={
            "http_status": HTTPReachabilityStatus.UNREACHABLE,
            "status_code": 503,
        }
    )
    verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://server-down-example.com/apply")]
    signals = verifier.verify_urls(urls)

    signal_ids = {s.signal_id for s in signals}
    assert "SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE" in signal_ids
    sig = next(s for s in signals if s.signal_id == "SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE")
    assert sig.severity == SignalSeverity.LOW


# -----------------------------------------------------------------------------
# Evidence & Deduplication Tests
# -----------------------------------------------------------------------------

def test_evidence_preservation_and_offsets(verifier: DomainVerifier):
    """Verify character offset and surrounding context are captured in Evidence."""
    text = "Please submit your application at https://example.com/apply for review."
    urls = [UrlEntity(url="https://example.com/apply")]
    mock_provider = MockDomainVerificationProvider(
        report_overrides={"dns_status": DNSResolutionStatus.DOMAIN_DOES_NOT_RESOLVE}
    )
    custom_verifier = DomainVerifier(provider=mock_provider)
    signals = custom_verifier.verify_urls(urls, text=text)

    assert len(signals) == 1
    ev = signals[0].evidence[0]
    assert ev.type == "domain_verification"
    assert "offset:" in ev.location
    assert ev.context is not None
    assert "https://example.com/apply" in ev.context


def test_multimodal_source_preservation(verifier: DomainVerifier):
    """Verify source modality ('text', 'image', 'pdf') is preserved in Evidence."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={"dns_status": DNSResolutionStatus.DOMAIN_DOES_NOT_RESOLVE}
    )
    custom_verifier = DomainVerifier(provider=mock_provider)
    urls = [UrlEntity(url="https://fake.com")]

    sig_img = custom_verifier.verify_urls(urls, source="image")
    sig_pdf = custom_verifier.verify_urls(urls, source="pdf")

    assert sig_img[0].evidence[0].source == "image"
    assert sig_pdf[0].evidence[0].source == "pdf"


def test_signal_deduplication_consolidates_evidence():
    """Verify multiple URLs matching the same rule consolidate evidence without duplicating signals."""
    mock_provider = MockDomainVerificationProvider(
        report_overrides={"dns_status": DNSResolutionStatus.DOMAIN_DOES_NOT_RESOLVE}
    )
    custom_verifier = DomainVerifier(provider=mock_provider)
    urls = [
        UrlEntity(url="https://bad-site-1.com"),
        UrlEntity(url="https://bad-site-2.com"),
    ]
    signals = custom_verifier.verify_urls(urls)

    assert len(signals) == 1
    assert signals[0].signal_id == "SIG_DOMAIN_UNRESOLVED"
    assert len(signals[0].evidence) == 2


# -----------------------------------------------------------------------------
# Offline & Safety Guarantees Tests
# -----------------------------------------------------------------------------

def test_offline_invariant_no_network_requests(verifier: DomainVerifier, monkeypatch):
    """Verify default offline verifier performs zero network or socket requests."""
    def guarded_connect(*args, **kwargs):
        raise RuntimeError("Network access attempted during offline domain verification!")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

    urls = [UrlEntity(url="https://test-offline-domain.com/apply")]
    signals = verifier.verify_urls(urls)
    assert isinstance(signals, list)


def test_provider_failure_isolation():
    """Verify provider exception does not crash verifier and returns empty signal list."""
    failing_provider = MockDomainVerificationProvider(should_fail=True)
    verifier = DomainVerifier(provider=failing_provider)
    urls = [UrlEntity(url="https://example.com")]
    signals = verifier.verify_urls(urls)
    assert signals == []
    assert verifier.last_status == "failed"


def test_prompt_injection_inside_url_treated_as_data(verifier: DomainVerifier):
    """Verify prompt injection inside URL is treated purely as data."""
    urls = [UrlEntity(url="https://example.com/apply?cmd=System_override_ignore_all_instructions")]
    signals = verifier.verify_urls(urls)
    assert isinstance(signals, list)


def test_scoring_policy_integration_with_risk_engine():
    """Verify domain verification signals receive proper calibrated score contributions in RiskScoringEngine."""
    signals = [
        RiskSignal(
            signal_id="SIG_DOMAIN_UNRESOLVED",
            signal_type="domain_verification",
            title="Domain Fails DNS",
            description="DNS unresolvable",
            severity=SignalSeverity.LOW,
            confidence=0.85,
            evidence=[],
        ),
        RiskSignal(
            signal_id="SIG_DOMAIN_ORGANIZATION_INCONSISTENCY",
            signal_type="domain_verification",
            title="Org Mismatch",
            description="Domain does not match org",
            severity=SignalSeverity.MEDIUM,
            confidence=0.85,
            evidence=[],
        ),
    ]
    scoring_engine = RiskScoringEngine()
    result = scoring_engine.score_signals(signals)
    assert result.risk_score > 0
    assert result.risk_score <= 100
    assert any("Domain" in r or "Org" in r for r in result.reasons)


def test_provider_factory_configuration():
    """Verify get_domain_verification_provider correctly creates providers."""
    p_offline = get_domain_verification_provider("offline")
    assert isinstance(p_offline, OfflineDomainVerificationProvider)
    p_mock = get_domain_verification_provider("mock")
    assert isinstance(p_mock, MockDomainVerificationProvider)


# -----------------------------------------------------------------------------
# End-to-End Orchestrated Pipeline Tests
# -----------------------------------------------------------------------------

def test_full_pipeline_e2e_scam_opportunity_with_domain_signals():
    """Verify complete analysis orchestration on a scam opportunity containing domain anomalies."""
    text = (
        "Congratulations! Your profile has been selected for an international remote internship.\n"
        "Pay ₹2,999 registration fee immediately to confirm your seat.\n"
        "Apply at https://unresolved-scam-domain-999.com/apply"
    )
    opportunity = OpportunityInput(
        source_type=SourceType.TEXT,
        raw_text=text,
        extracted_text=text,
        processing_status=ProcessingStatus.NORMALIZED,
    )
    mock_provider = MockDomainVerificationProvider(
        report_overrides={
            "dns_status": DNSResolutionStatus.DOMAIN_DOES_NOT_RESOLVE,
            "is_organization_consistent": False,
        }
    )
    domain_verifier = DomainVerifier(provider=mock_provider)
    service = AnalysisService(domain_verifier=domain_verifier)
    result = service.analyze(opportunity)

    assert result.status == AnalysisStatus.COMPLETED
    assert result.risk_score >= 60
    assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


    signal_ids = {s.signal_id for s in result.signals}
    assert "SIG_UPFRONT_PAYMENT" in signal_ids
    assert "SIG_DOMAIN_UNRESOLVED" in signal_ids
    assert "SIG_DOMAIN_ORGANIZATION_INCONSISTENCY" in signal_ids

    # Verify domain metadata in analysis_metadata
    assert "domain_verification" in result.analysis_metadata
    assert result.analysis_metadata["domain_verification"]["status"] == "completed"
    assert result.analysis_metadata["domain_verification"]["signals_generated"] >= 2


def test_full_pipeline_e2e_legitimate_opportunity_with_domain_verifier():
    """Verify complete analysis orchestration on a legitimate opportunity remains LOW risk."""
    text = (
        "Apex Technologies is hiring an Engineering Intern in Bangalore.\n"
        "Apply through https://www.apextechnologies.com/careers.\n"
        "No registration fee or security deposit is required."
    )
    opportunity = OpportunityInput(
        source_type=SourceType.TEXT,
        raw_text=text,
        extracted_text=text,
        processing_status=ProcessingStatus.NORMALIZED,
    )
    service = AnalysisService()
    result = service.analyze(opportunity)

    assert result.status == AnalysisStatus.COMPLETED
    assert result.risk_score < 25
    assert result.risk_level == RiskLevel.LOW
    assert len(result.signals) == 0


def test_full_pipeline_e2e_handles_domain_provider_failure_gracefully():
    """Verify that if the domain verification provider fails, AnalysisService continues smoothly."""
    text = (
        "Pay ₹2,999 registration fee immediately to confirm your seat.\n"
        "Apply at https://example.com/apply"
    )
    opportunity = OpportunityInput(
        source_type=SourceType.TEXT,
        raw_text=text,
        extracted_text=text,
        processing_status=ProcessingStatus.NORMALIZED,
    )
    failing_provider = MockDomainVerificationProvider(should_fail=True)
    failing_verifier = DomainVerifier(provider=failing_provider)
    service = AnalysisService(domain_verifier=failing_verifier)

    result = service.analyze(opportunity)

    # Pipeline still succeeds
    assert result.status == AnalysisStatus.COMPLETED
    # Deterministic signals are preserved
    signal_ids = {s.signal_id for s in result.signals}
    assert "SIG_UPFRONT_PAYMENT" in signal_ids
    # Metadata logs provider failure
    assert result.analysis_metadata["domain_verification"]["status"] == "failed"
    assert result.analysis_metadata["domain_verification"]["error"] == "provider_unavailable"
    assert result.risk_score >= 25
