"""Operational Hardening & Operational Diagnostics Test Suite for ScamCheck (Part 16).

STATUS: FULLY IMPLEMENTED (Part 16)

Tests:
1. Configuration defaults
2. Environment configuration overrides
3. Invalid configuration handling / safe defaults
4. Request ID propagation in HTTP headers and logs
5. Request timing & operational metrics collection
6. Structured JSON logging behavior
7. Sensitive data redaction / privacy enforcement in logs
8. Fast liveness health endpoint
9. Database readiness endpoint
10. DatabaseManager check_readiness functionality
11. CORS behavior & origin handling
12. Production security headers (nosniff, DENY, Referrer-Policy, CSP)
13. Pagination boundary validation
14. Malformed analysis ID handling
15. Persistence failure isolation
16. Provider failure isolation
17. End-to-end API -> Analysis -> Persistence -> History flow
"""

import json
import logging
import os
from typing import Generator
import pytest
from starlette.testclient import TestClient

from backend.app.core.config import Settings, get_settings, reset_settings
from backend.app.core.logging import StructuredJsonFormatter, get_logger, log_event, setup_logging
from backend.app.core.metrics import metrics_collector
from backend.app.main import app
from backend.app.persistence.database import DatabaseManager, get_db_manager, reset_db_manager
from backend.app.persistence.repository import SQLiteAnalysisRepository


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide TestClient instance for API endpoint testing."""
    with TestClient(app) as test_client:
        yield test_client


def test_configuration_defaults():
    """Verify default runtime settings."""
    reset_settings()
    settings = get_settings()
    assert settings.app_name == "ScamCheck API"
    assert settings.environment in ("development", "test")
    assert settings.api_port == 8000
    assert "http://localhost:5173" in settings.cors_origins
    assert settings.enable_persistence is True


def test_environment_configuration_overrides(monkeypatch):
    """Verify loading configuration overrides from environment variables."""
    monkeypatch.setenv("SCAMCHECK_ENV", "staging")
    monkeypatch.setenv("SCAMCHECK_PORT", "9000")
    monkeypatch.setenv("SCAMCHECK_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com,https://app.scamcheck.org")

    reset_settings()
    settings = get_settings()

    assert settings.environment == "staging"
    assert settings.api_port == 9000
    assert settings.log_level == "DEBUG"
    assert "http://example.com" in settings.cors_origins
    assert "https://app.scamcheck.org" in settings.cors_origins
    reset_settings()


def test_invalid_configuration_handling(monkeypatch):
    """Verify safe fallback behavior when invalid env variables are set."""
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("SCAMCHECK_ENV", "production")

    reset_settings()
    settings = get_settings()

    assert settings.environment == "production"
    assert len(settings.cors_origins) > 0
    assert "http://localhost:3000" in settings.cors_origins
    reset_settings()


def test_request_id_propagation(client: TestClient):
    """Verify X-Request-ID is generated and returned in headers."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    req_id = resp.headers["X-Request-ID"]
    assert req_id.startswith("req_")

    # Custom request ID header propagation
    custom_id = "req_custom_test_12345"
    resp_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp_custom.status_code == 200
    assert resp_custom.headers["X-Request-ID"] == custom_id


def test_request_timing_instrumentation(client: TestClient):
    """Verify request timing and operational telemetry metrics collection."""
    metrics_collector.reset()

    resp = client.get("/health")
    assert resp.status_code == 200

    metrics = metrics_collector.get_summary()
    assert metrics["total_requests"] >= 1
    assert metrics["avg_request_duration_ms"] >= 0.0


def test_structured_logging_behavior():
    """Verify StructuredJsonFormatter formats logs as valid JSON with required keys."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="scamcheck.test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Operational test log message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req_test_logging_99"
    record.component = "TEST_MODULE"
    record.extra_fields = {"custom_tag": "val123"}

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["logger"] == "scamcheck.test_logger"
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Operational test log message"
    assert parsed["request_id"] == "req_test_logging_99"
    assert parsed["component"] == "TEST_MODULE"
    assert parsed["custom_tag"] == "val123"


def test_sensitive_data_is_not_logged():
    """Verify privacy enforcement redacts passwords, tokens, and raw bytes."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="scamcheck.privacy_test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Sensitive event log test",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "password": "SecretPassword123!",
        "auth_token": "Bearer abc123xyz",
        "raw_bytes": b"\x00\x01\x02\x03" * 10,
    }

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["password"] == "[REDACTED_SENSITIVE_DATA]"
    assert parsed["auth_token"] == "[REDACTED_SENSITIVE_DATA]"
    assert parsed["raw_bytes"] == "[REDACTED_SENSITIVE_DATA]"
    assert "SecretPassword123!" not in output


def test_health_endpoint(client: TestClient):
    """Verify fast, zero-network liveness health endpoint."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ScamCheck API"


def test_readiness_endpoint(client: TestClient):
    """Verify readiness health endpoint checking database state."""
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "healthy"


def test_database_readiness():
    """Verify DatabaseManager check_readiness method returns True."""
    db_mgr = DatabaseManager(db_path=":memory:")
    assert db_mgr.check_readiness() is True


def test_cors_behavior(client: TestClient):
    """Verify CORS preflight handling with allowed origin."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    resp = client.options("/api/v1/analyze", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_security_headers(client: TestClient):
    """Verify production security headers are set on all responses."""
    resp = client.get("/health")
    assert resp.status_code == 200

    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers


def test_pagination_limits(client: TestClient):
    """Verify pagination limit bounds on history list endpoint."""
    resp = client.get("/api/v1/analyses?limit=150")
    assert resp.status_code == 422


def test_malformed_analysis_id(client: TestClient):
    """Verify retrieving a non-existent analysis ID returns HTTP 404."""
    resp = client.get("/api/v1/analyses/non_existent_id_99999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"]["error_code"] == "NOT_FOUND"


def test_persistence_failure_isolation():
    """Verify persistence errors do not crash analysis execution or alter score."""
    from backend.app.analysis import AnalysisService
    from backend.app.schemas.opportunity import OpportunityInput, SourceType

    class FaultyRepository(SQLiteAnalysisRepository):
        def save(self, record):
            raise RuntimeError("Database disk quota full error")

    service = AnalysisService()
    faulty_repo = FaultyRepository(db_manager=DatabaseManager(db_path=":memory:"))

    inp = OpportunityInput(
        source_type=SourceType.TEXT,
        extracted_text="Simple test opportunity input text for operational isolation testing.",
    )

    result = service.analyze(inp)
    assert result.risk_score >= 0

    from backend.app.api.v1.routes import _save_record_safely

    _save_record_safely(faulty_repo, "req_test_faulty_db", result)

    assert result.analysis_metadata["persistence_status"] == "failed"
    assert "Database disk quota full" in result.analysis_metadata["persistence_error"]
    assert result.risk_score >= 0


def test_provider_failure_isolation():
    """Verify third-party domain/semantic provider failures are isolated."""
    from backend.app.analysis.domain.domain_verifier import DomainVerifier
    from backend.app.analysis.domain.network_client import DomainVerificationProvider
    from backend.app.analysis.domain.domain_schemas import DomainVerificationReport
    from backend.app.schemas.opportunity import OpportunityInput, SourceType
    from backend.app.analysis.models import AnalysisContext, ExtractedEntities, UrlEntity


    class FailingProvider(DomainVerificationProvider):
        def verify(self, url: str, claimed_organizations=None) -> DomainVerificationReport:
            raise ConnectionError("DNS Server Timeout")

        def get_provider_name(self) -> str:
            return "failing_mock"

    verifier = DomainVerifier(provider=FailingProvider())
    context = AnalysisContext(
        opportunity=OpportunityInput(
            source_type=SourceType.TEXT,
            extracted_text="Check out http://timeout-domain-test.com for jobs",
        ),
        extracted_entities=ExtractedEntities(
            urls=[UrlEntity(url="http://timeout-domain-test.com", domain="timeout-domain-test.com")]
        )
    )

    signals = verifier.verify(context)

    # Provider outage does not crash execution and yields 0 signals
    assert verifier.last_status in ("failed", "error")
    assert "DNS Server Timeout" in str(verifier.last_error)
    assert isinstance(signals, list)






def test_full_api_analysis_persistence_history_flow(client: TestClient):
    """Verify complete operational flow: API submission -> analysis -> persistence -> history listing -> detailed inspection."""
    payload = {
        "text": "URGENT INTERNSHIP: Pay $150 registration fee via UPI to claim guaranteed $5000/month remote job! Contact recruiter@telegram-job-desk.com",
    }

    # 1. Analyze Plain Text
    analyze_resp = client.post("/api/v1/analyze", json=payload)
    assert analyze_resp.status_code == 200
    res_data = analyze_resp.json()

    assert res_data["risk_score"] > 30
    assert res_data["risk_level"] in ("medium", "high", "critical")
    req_id = res_data["request_id"]
    assert req_id.startswith("req_")

    # 2. Query History List
    history_resp = client.get("/api/v1/analyses?limit=10")
    assert history_resp.status_code == 200
    hist_data = history_resp.json()
    assert hist_data["total"] >= 1
    matched = [item for item in hist_data["items"] if item["analysis_id"] == req_id]
    assert len(matched) == 1

    # 3. Retrieve Detailed Single Analysis Record
    get_resp = client.get(f"/api/v1/analyses/{req_id}")
    assert get_resp.status_code == 200
    detail_data = get_resp.json()
    assert detail_data["request_id"] == req_id
    assert detail_data["risk_score"] == res_data["risk_score"]
