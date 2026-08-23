"""ScamCheck Persistence Package.

STATUS: FULLY IMPLEMENTED (Part 14)

Exports:
- AnalysisRepository
- SQLiteAnalysisRepository
- get_analysis_repository
- AnalysisRecord
- AnalysisSummaryItem
- AnalysisListResponse
- DatabaseManager
- get_db_manager
- reset_db_manager
"""

from backend.app.persistence.database import (
    DatabaseManager,
    get_db_manager,
    reset_db_manager,
)
from backend.app.persistence.models import (
    AnalysisListResponse,
    AnalysisRecord,
    AnalysisSummaryItem,
)
from backend.app.persistence.repository import (
    AnalysisRepository,
    SQLiteAnalysisRepository,
    get_analysis_repository,
)

__all__ = [
    "AnalysisListResponse",
    "AnalysisRecord",
    "AnalysisRepository",
    "AnalysisSummaryItem",
    "DatabaseManager",
    "SQLiteAnalysisRepository",
    "get_analysis_repository",
    "get_db_manager",
    "reset_db_manager",
]
