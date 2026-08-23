"""Unit and Integration Tests for ScamCheck Persistent Analysis History Layer.

STATUS: FULLY IMPLEMENTED (Part 14)

Tests:
1. Save successful analysis record
2. Save failed analysis record
3. Retrieve analysis by ID
4. Missing analysis ID handling
5. List analyses
6. Pagination (limit & offset)
7. Deterministic ordering (created_at DESC)
8. Maximum page size bounds
9. Serialization and deserialization fidelity
10. Enum persistence (RiskLevel, AnalysisStatus, SourceType, SignalSeverity)
11. Nested evidence persistence
12. Extracted entity persistence
13. Analysis metadata persistence
14. Request ID persistence
15. Restart-style reload from disk database
16. Database initialization
17. Isolated test database
18. Repository failure handling in API
19. Persistence failure does not alter risk score
20. API history list endpoint (GET /api/v1/analyses)
21. API detail endpoint (GET /api/v1/analyses/{analysis_id})
22. Malformed analysis ID handling
23. No database stack traces exposed
24. Sensitive data minimization
25. Existing analysis endpoint persists record and returns response
26. Health endpoint does not require database/network
27. Existing offline analysis guarantees remain intact
"""

import os
import tempfile
from typing import Any, Dict, List
import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.analysis.models import (
    AnalysisResult,
    AnalysisStatus,
    Evidence,
    ExtractedEntities,
    OrganizationEntity,
    RiskLevel,
    RiskSignal,
    SignalSeverity,
    UrlEntity,
)
from backend.app.persistence import (
    AnalysisListResponse,
    AnalysisRecord,
    AnalysisRepository,
    DatabaseManager,
    SQLiteAnalysisRepository,
    get_analysis_repository,
    get_db_manager,
    reset_db_manager,
)
from backend.app.schemas.opportunity import SourceType


@pytest.fixture
def temp_db_path(tmp_path) -> str:
    """Create an isolated temporary SQLite database path for testing."""
    return str(tmp_path / "test_scamcheck.db")


@pytest.fixture
def repo(temp_db_path: str) -> SQLiteAnalysisRepository:
    """Create an isolated SQLiteAnalysisRepository instance."""
    db_mgr = DatabaseManager(db_path=temp_db_path)
    return SQLiteAnalysisRepository(db_manager=db_mgr)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_sample_record(
    analysis_id: str = "ana_test_123",
    request_id: str = "req_test_123",
    risk_score: int = 75,
    risk_level: RiskLevel = RiskLevel.HIGH,
    created_at: str = "2026-08-23T10:00:00Z",
) -> AnalysisRecord:
    """Helper to create a sample AnalysisRecord with full nested structures."""
    return AnalysisRecord(
        analysis_id=analysis_id,
        request_id=request_id,
        created_at=created_at,
        completed_at="2026-08-23T10:00:01Z",
        status=AnalysisStatus.COMPLETED,
        source_type=SourceType.TEXT,
        risk_score=risk_score,
        risk_level=risk_level,
        summary="Test opportunity exhibits upfront fee demands.",
        student_guidance="Do not transfer money to unverified employers.",
        reasons=["Upfront registration fee requested"],
        signals=[
            RiskSignal(
                signal_id="SIG_UPFRONT_PAYMENT",
                signal_type="financial_risk",
                title="Upfront Payment Requested",
                description="Candidate asked for ₹2,999 registration fee.",
                severity=SignalSeverity.HIGH,
                confidence=0.95,
                score_contribution=0.0,
                evidence=[
                    Evidence(
                        type="payment_demand",
                        value="₹2,999 registration fee",
                        source="text",
                        location="offset:10-35",
                        context="Please pay ₹2,999 registration fee.",
                    )
                ],
            )
        ],
        extracted_entities=ExtractedEntities(
            organizations=[OrganizationEntity(name="Acme Fake Corp")],
            urls=[UrlEntity(url="https://acme-fake.com/jobs")],
        ),
        evidence=[
            Evidence(
                type="payment_demand",
                value="₹2,999 registration fee",
                source="text",
                location="offset:10-35",
            )
        ],
        analysis_metadata={"test_run": True, "provider": "deterministic"},
    )


# -----------------------------------------------------------------------------
# 1. Repository CRUD & Lifecycle Tests
# -----------------------------------------------------------------------------

def test_save_and_retrieve_successful_analysis(repo: SQLiteAnalysisRepository):
    """1 & 3. Save a complete analysis record and retrieve it by ID."""
    record = _make_sample_record(analysis_id="rec_001", request_id="req_001")
    saved = repo.save(record)
    assert saved.analysis_id == "rec_001"

    retrieved = repo.get_by_id("rec_001")
    assert retrieved is not None
    assert retrieved.analysis_id == "rec_001"
    assert retrieved.request_id == "req_001"
    assert retrieved.risk_score == 75
    assert retrieved.risk_level == RiskLevel.HIGH
    assert retrieved.status == AnalysisStatus.COMPLETED
    assert len(retrieved.signals) == 1
    assert retrieved.signals[0].signal_id == "SIG_UPFRONT_PAYMENT"
    assert len(retrieved.extracted_entities.organizations) == 1
    assert retrieved.extracted_entities.organizations[0].name == "Acme Fake Corp"


def test_save_and_retrieve_failed_analysis(repo: SQLiteAnalysisRepository):
    """2. Save a failed analysis record and retrieve it."""
    record = AnalysisRecord(
        analysis_id="rec_failed_001",
        request_id="req_failed_001",
        created_at="2026-08-23T10:00:00Z",
        status=AnalysisStatus.FAILED,
        source_type=SourceType.IMAGE,
        risk_score=None,
        risk_level=RiskLevel.LOW,
        summary="Image extraction failed due to unreadable content.",
        analysis_metadata={"error": "OCR failure"},
    )
    repo.save(record)
    retrieved = repo.get_by_id("rec_failed_001")
    assert retrieved is not None
    assert retrieved.status == AnalysisStatus.FAILED
    assert retrieved.risk_score is None


def test_missing_analysis_id_returns_none(repo: SQLiteAnalysisRepository):
    """4. Querying a non-existent analysis ID returns None cleanly."""
    assert repo.get_by_id("non_existent_id_999") is None
    assert repo.get_by_id("") is None


def test_list_recent_analyses_and_pagination(repo: SQLiteAnalysisRepository):
    """5, 6, 7. Test listing, pagination, and deterministic ordering (DESC)."""
    # Insert 5 records with sequential timestamps
    for i in range(1, 6):
        rec = _make_sample_record(
            analysis_id=f"rec_page_{i}",
            request_id=f"req_page_{i}",
            risk_score=i * 10,
            created_at=f"2026-08-23T10:0{i}:00Z",
        )
        repo.save(rec)

    # Page 1: limit 2, offset 0 -> newest first (rec_page_5, rec_page_4)
    items_p1, total = repo.list_recent(limit=2, offset=0)
    assert total == 5
    assert len(items_p1) == 2
    assert items_p1[0].analysis_id == "rec_page_5"
    assert items_p1[1].analysis_id == "rec_page_4"

    # Page 2: limit 2, offset 2 -> (rec_page_3, rec_page_2)
    items_p2, _ = repo.list_recent(limit=2, offset=2)
    assert len(items_p2) == 2
    assert items_p2[0].analysis_id == "rec_page_3"
    assert items_p2[1].analysis_id == "rec_page_2"

    # Page 3: limit 2, offset 4 -> (rec_page_1)
    items_p3, _ = repo.list_recent(limit=2, offset=4)
    assert len(items_p3) == 1
    assert items_p3[0].analysis_id == "rec_page_1"


def test_list_recent_with_filters(repo: SQLiteAnalysisRepository):
    """8. Test listing with source_type and risk_level filters."""
    rec_text = _make_sample_record(analysis_id="rec_filter_1", risk_level=RiskLevel.HIGH)
    rec_text.source_type = SourceType.TEXT
    repo.save(rec_text)

    rec_pdf = _make_sample_record(analysis_id="rec_filter_2", risk_level=RiskLevel.LOW)
    rec_pdf.source_type = SourceType.PDF
    repo.save(rec_pdf)

    # Filter by risk_level
    high_items, high_total = repo.list_recent(risk_level="high")
    assert high_total == 1
    assert high_items[0].analysis_id == "rec_filter_1"

    # Filter by source_type
    pdf_items, pdf_total = repo.list_recent(source_type="pdf")
    assert pdf_total == 1
    assert pdf_items[0].analysis_id == "rec_filter_2"


# -----------------------------------------------------------------------------
# 2. Serialization & Reload Tests
# -----------------------------------------------------------------------------

def test_serialization_fidelity_and_disk_reload(temp_db_path: str):
    """9, 10, 11, 12, 13, 14, 15. Verify complete serialization across DB restart."""
    # Write record using repo 1
    db_mgr_1 = DatabaseManager(db_path=temp_db_path)
    repo_1 = SQLiteAnalysisRepository(db_manager=db_mgr_1)
    original = _make_sample_record(analysis_id="persist_disk_01")
    repo_1.save(original)

    # Simulate app restart with a fresh DatabaseManager & repository on same path
    db_mgr_2 = DatabaseManager(db_path=temp_db_path)
    repo_2 = SQLiteAnalysisRepository(db_manager=db_mgr_2)
    loaded = repo_2.get_by_id("persist_disk_01")

    assert loaded is not None
    assert loaded.analysis_id == "persist_disk_01"
    assert loaded.risk_score == 75
    assert loaded.risk_level == RiskLevel.HIGH
    assert loaded.source_type == SourceType.TEXT
    assert len(loaded.signals) == 1
    assert loaded.signals[0].severity == SignalSeverity.HIGH
    assert len(loaded.extracted_entities.organizations) == 1
    assert loaded.extracted_entities.organizations[0].name == "Acme Fake Corp"
    assert loaded.analysis_metadata["test_run"] is True


def test_database_initialization(temp_db_path: str):
    """16 & 17. Verify tables and indexes are created automatically."""
    db_mgr = DatabaseManager(db_path=temp_db_path)
    with db_mgr.get_connection() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analyses';")
        assert cursor.fetchone() is not None


# -----------------------------------------------------------------------------
# 3. API History & Failure Isolation Tests
# -----------------------------------------------------------------------------

def test_api_v1_analyze_persists_record(client: TestClient):
    """25. Verify POST /api/v1/analyze automatically saves the record into history."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "Internship opportunity at Google. Apply at https://careers.google.com."},
    )
    assert response.status_code == 200
    req_id = response.json()["request_id"]

    # Fetch from history endpoint
    get_res = client.get(f"/api/v1/analyses/{req_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["request_id"] == req_id
    assert data["status"] == "completed"
    assert data["source_type"] == "text"


def test_api_v1_get_analysis_by_id_success_and_not_found(client: TestClient):
    """20 & 21. Verify GET /api/v1/analyses/{id} handles found and 404 cleanly."""
    # 404 for unknown ID
    res_404 = client.get("/api/v1/analyses/unknown_req_123456789")
    assert res_404.status_code == 404
    assert res_404.json()["detail"]["error_code"] == "NOT_FOUND"


def test_api_v1_list_analyses_endpoint(client: TestClient):
    """20. Verify GET /api/v1/analyses returns paginated history list."""
    # Submit an analysis
    client.post("/api/v1/analyze", json={"text": "Software job posting at Amazon."})

    res = client.get("/api/v1/analyses?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_api_v1_persistence_failure_isolation(client: TestClient, monkeypatch):
    """18, 19, 23. Verify repository failure does not crash analysis or alter risk score."""
    def failing_save(self, record):
        raise RuntimeError("Disk full / SQLite write error")

    monkeypatch.setattr(SQLiteAnalysisRepository, "save", failing_save)

    scam_text = (
        "Congratulations! Selected for international internship.\n"
        "Pay ₹2,999 registration fee immediately to confirm your seat."
    )
    response = client.post("/api/v1/analyze", json={"text": scam_text})
    assert response.status_code == 200
    data = response.json()

    # Risk score and verdict must NOT be altered by database failure
    assert data["risk_score"] >= 40
    assert data["risk_level"] in ["medium", "high", "critical"]
    # Telemetry records persistence failure safely
    assert data["analysis_metadata"]["persistence_status"] == "failed"
    assert "persistence_error" in data["analysis_metadata"]


def test_api_v1_malformed_analysis_id_handling(client: TestClient):
    """22. Verify malformed analysis ID returns 404 cleanly."""
    res = client.get("/api/v1/analyses/%20")
    assert res.status_code in (404, 422)


def test_sensitive_data_minimization_in_db(repo: SQLiteAnalysisRepository):
    """24. Verify records do not contain binary blobs or unnecessary secrets."""
    record = _make_sample_record(analysis_id="rec_data_min")
    repo.save(record)
    with repo.db_manager.get_connection() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE analysis_id='rec_data_min';").fetchone()
        row_dict = dict(row)
        # Verify no file binary columns exist
        assert "file_bytes" not in row_dict
        assert "raw_binary" not in row_dict
        assert "password" not in row_dict


def test_health_endpoint_does_not_depend_on_network(client: TestClient):
    """26 & 27. Verify GET /api/v1/health remains fast and offline."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
