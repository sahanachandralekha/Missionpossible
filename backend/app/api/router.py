"""ScamCheck API Router Aggregator.

STATUS: FULLY IMPLEMENTED (Part 13)

Aggregates:
- /api/v1 (Production V1 API routes for plain text, image OCR, PDF, and health)
- /api/analyze (Legacy backward-compatible foundation routes)
"""

from fastapi import APIRouter
from backend.app.api.v1.routes import router as v1_router
from backend.app.api.routes.analysis import router as legacy_analysis_router

api_router = APIRouter()
api_router.include_router(v1_router)
api_router.include_router(legacy_analysis_router)

__all__ = ["api_router", "v1_router", "legacy_analysis_router"]
