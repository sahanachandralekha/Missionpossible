"""Analysis Repository Abstraction and SQLite Implementation for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 14)

Provides:
- AnalysisRepository (Abstract Base Class)
- SQLiteAnalysisRepository (Thread-safe, durable SQLite repository)
- get_analysis_repository (Dependency injector / factory)
"""

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.enums import AnalysisStatus, RiskLevel
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.persistence.database import DatabaseManager, get_db_manager
from backend.app.persistence.models import (
    AnalysisRecord,
    AnalysisSummaryItem,
)
from backend.app.schemas.opportunity import SourceType


class AnalysisRepository(ABC):
    """Abstract interface for persisting and querying analysis history records."""

    @abstractmethod
    def save(self, record: AnalysisRecord) -> AnalysisRecord:
        """Persist or update an analysis record."""
        pass

    @abstractmethod
    def get_by_id(self, analysis_id: str) -> Optional[AnalysisRecord]:
        """Retrieve a full analysis record by its unique identifier."""
        pass

    @abstractmethod
    def list_recent(
        self,
        limit: int = 20,
        offset: int = 0,
        source_type: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> Tuple[List[AnalysisSummaryItem], int]:
        """Query paginated recent analysis summaries with total count."""
        pass


class SQLiteAnalysisRepository(AnalysisRepository):
    """Durable SQLite implementation of AnalysisRepository."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db_manager = db_manager or get_db_manager()

    def save(self, record: AnalysisRecord) -> AnalysisRecord:
        """Persist an analysis record to the SQLite database."""
        sql = """
        INSERT OR REPLACE INTO analyses (
            analysis_id, request_id, created_at, completed_at, status, source_type,
            risk_score, risk_level, summary, student_guidance, reasons_json,
            signals_json, extracted_entities_json, evidence_json, analysis_metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        reasons_json = json.dumps(record.reasons)
        signals_json = json.dumps([s.model_dump(mode="json") for s in record.signals])
        extracted_entities_json = json.dumps(record.extracted_entities.model_dump(mode="json"))
        evidence_json = json.dumps([e.model_dump(mode="json") for e in record.evidence])
        analysis_metadata_json = json.dumps(record.analysis_metadata)

        source_type_val = (
            record.source_type.value
            if hasattr(record.source_type, "value")
            else str(record.source_type)
        )
        status_val = (
            record.status.value
            if hasattr(record.status, "value")
            else str(record.status)
        )
        risk_level_val = (
            record.risk_level.value
            if hasattr(record.risk_level, "value")
            else str(record.risk_level)
        )

        with self.db_manager.get_connection() as conn:
            conn.execute(
                sql,
                (
                    record.analysis_id,
                    record.request_id,
                    record.created_at,
                    record.completed_at,
                    status_val,
                    source_type_val,
                    record.risk_score,
                    risk_level_val,
                    record.summary,
                    record.student_guidance,
                    reasons_json,
                    signals_json,
                    extracted_entities_json,
                    evidence_json,
                    analysis_metadata_json,
                ),
            )
            conn.commit()
        return record

    def get_by_id(self, analysis_id: str) -> Optional[AnalysisRecord]:
        """Fetch and deserialize a complete analysis record by analysis_id."""
        if not analysis_id:
            return None

        sql = "SELECT * FROM analyses WHERE analysis_id = ? LIMIT 1;"
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, (analysis_id.strip(),))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def list_recent(
        self,
        limit: int = 20,
        offset: int = 0,
        source_type: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> Tuple[List[AnalysisSummaryItem], int]:
        """Fetch paginated summary records with filtering support."""
        where_clauses = []
        params: List[Any] = []

        if source_type:
            where_clauses.append("source_type = ?")
            params.append(source_type.lower())
        if risk_level:
            where_clauses.append("risk_level = ?")
            params.append(risk_level.lower())

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_sql = f"SELECT COUNT(*) AS total FROM analyses {where_sql};"
        query_sql = f"""
        SELECT * FROM analyses
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """

        with self.db_manager.get_connection() as conn:
            # Get total count
            count_cursor = conn.execute(count_sql, params)
            total = count_cursor.fetchone()["total"]

            # Query page
            page_params = list(params) + [max(1, limit), max(0, offset)]
            cursor = conn.execute(query_sql, page_params)
            rows = cursor.fetchall()

            items = [self._row_to_record(r).to_summary() for r in rows]
            return items, total

    def _row_to_record(self, row: sqlite3.Row) -> AnalysisRecord:
        """Convert a SQLite row into an AnalysisRecord."""
        reasons = json.loads(row["reasons_json"] or "[]")
        signals_raw = json.loads(row["signals_json"] or "[]")
        signals = [RiskSignal(**s) for s in signals_raw]

        entities_raw = json.loads(row["extracted_entities_json"] or "{}")
        extracted_entities = ExtractedEntities(**entities_raw)

        evidence_raw = json.loads(row["evidence_json"] or "[]")
        evidence = [Evidence(**e) for e in evidence_raw]

        analysis_metadata = json.loads(row["analysis_metadata_json"] or "{}")

        return AnalysisRecord(
            analysis_id=row["analysis_id"],
            request_id=row["request_id"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            status=AnalysisStatus(row["status"]),
            source_type=SourceType(row["source_type"]),
            risk_score=row["risk_score"],
            risk_level=RiskLevel(row["risk_level"]),
            summary=row["summary"],
            student_guidance=row["student_guidance"],
            reasons=reasons,
            signals=signals,
            extracted_entities=extracted_entities,
            evidence=evidence,
            analysis_metadata=analysis_metadata,
        )


def get_analysis_repository(db_manager: Optional[DatabaseManager] = None) -> AnalysisRepository:
    """Factory creating an AnalysisRepository instance."""
    return SQLiteAnalysisRepository(db_manager=db_manager)
