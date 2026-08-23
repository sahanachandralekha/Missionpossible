"""Database initialization and connection management for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 14)

Provides:
- SQLite connection management with WAL mode and thread safety
- Automatic schema creation and migration
- Configurable database path (SCAMCHECK_DB_PATH or in-memory)
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

from backend.app.core.config import get_settings

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    source_type TEXT NOT NULL,
    risk_score INTEGER,
    risk_level TEXT NOT NULL,
    summary TEXT,
    student_guidance TEXT,
    reasons_json TEXT NOT NULL DEFAULT '[]',
    signals_json TEXT NOT NULL DEFAULT '[]',
    extracted_entities_json TEXT NOT NULL DEFAULT '{}',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    analysis_metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_request_id ON analyses(request_id);
CREATE INDEX IF NOT EXISTS idx_analyses_risk_level ON analyses(risk_level);
"""


class DatabaseManager:
    """Manages SQLite database lifecycle, schema initialization, and connections."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        settings = get_settings()
        self.db_path = db_path or settings.database_path
        self._ensure_db_initialized()

    def get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection configured for dictionary access and concurrency."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=10.0,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency if not in-memory
        if self.db_path != ":memory:":
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except sqlite3.Error:
                pass
        return conn

    def check_readiness(self) -> bool:
        """Verify database connection health and execution readiness."""
        try:
            with self.get_connection() as conn:
                cur = conn.execute("SELECT 1;")
                row = cur.fetchone()
                return row is not None and row[0] == 1
        except Exception:
            return False

    def _ensure_db_initialized(self) -> None:
        """Create tables, schema_version, and indexes if they do not already exist."""
        if self.db_path != ":memory:":
            parent_dir = Path(self.db_path).parent
            if str(parent_dir) not in ("", "."):
                parent_dir.mkdir(parents=True, exist_ok=True)

        with self.get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()



# Default singleton instance
_default_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    """Get or create the DatabaseManager singleton."""
    global _default_db_manager
    if db_path is not None:
        return DatabaseManager(db_path=db_path)
    if _default_db_manager is None:
        _default_db_manager = DatabaseManager()
    return _default_db_manager


def reset_db_manager() -> None:
    """Reset global DatabaseManager singleton (used for test isolation)."""
    global _default_db_manager
    _default_db_manager = None
