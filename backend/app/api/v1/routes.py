"""Version 1 API Routes for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 14)

Provides:
- POST /api/v1/analyze (JSON Plain text opportunity analysis & persistence)
- POST /api/v1/analyze/file (Multipart Image/PDF opportunity analysis & persistence)
- GET /api/v1/analyses (Paginated analysis history list with filtering)
- GET /api/v1/analyses/{analysis_id} (Detailed analysis retrieval by ID)
- GET /api/v1/health (Fast, offline health & readiness check)

Architectural Invariant:
HTTP Request -> Validation -> Ingestion (InputService) -> AnalysisService -> AnalysisResult -> AnalysisRepository (safe persistence) -> AnalysisApiResponse
No business logic or scoring calculations in the API routing layer.
"""

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from backend.app.api.schemas import (
    AnalysisApiResponse,
    AnalysisListResponse,
    AnalyzeTextRequest,
    ApiErrorResponse,
    ApiHealthResponse,
)
from backend.app.analysis import AnalysisService
from backend.app.analysis.models import AnalysisResult, AnalysisStatus
from backend.app.persistence import (
    AnalysisRecord,
    AnalysisRepository,
    get_analysis_repository,
)
from backend.app.schemas.opportunity import OpportunityInput
from backend.app.services.input_service import InputService

router = APIRouter(prefix="/api/v1", tags=["Analysis V1"])


def get_input_service() -> InputService:
    """Dependency injector for InputService."""
    return InputService()


def get_analysis_service() -> AnalysisService:
    """Dependency injector for AnalysisService."""
    return AnalysisService()


def get_repository() -> AnalysisRepository:
    """Dependency injector for AnalysisRepository."""
    return get_analysis_repository()


from backend.app.core.middleware import get_current_request_id


def extract_or_generate_request_id(
    header_id: Optional[str] = None,
    payload_id: Optional[str] = None,
) -> str:
    """Extract client header or payload request ID, or use active request context correlation ID."""
    for candidate in (header_id, payload_id):
        if candidate:
            clean = candidate.strip()
            if re.match(r"^[a-zA-Z0-9_-]{1,128}$", clean):
                return clean
    ctx_id = get_current_request_id()
    if ctx_id:
        return ctx_id
    return f"req_{uuid.uuid4().hex[:16]}"


from backend.app.core.logging import get_logger, log_event
from backend.app.core.metrics import metrics_collector

logger = get_logger("api_v1")


def _save_record_safely(
    repository: AnalysisRepository,
    request_id: str,
    result: AnalysisResult,
) -> None:
    """Persist an analysis result to the database with strict failure isolation."""
    try:
        created_time = result.created_at or datetime.now(timezone.utc).isoformat()
        record = AnalysisRecord(
            analysis_id=request_id,
            request_id=request_id,
            created_at=created_time,
            completed_at=datetime.now(timezone.utc).isoformat(),
            status=result.status,
            source_type=result.source_type,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            summary=result.summary,
            student_guidance=result.student_guidance,
            reasons=result.reasons,
            signals=result.signals,
            extracted_entities=result.extracted_entities,
            evidence=result.evidence,
            analysis_metadata=result.analysis_metadata,
        )
        repository.save(record)
        result.analysis_metadata["persistence_status"] = "saved"
        metrics_collector.record_persistence(success=True)
        log_event(
            logger,
            10 if hasattr(logger, "DEBUG") else 20, # INFO
            "Analysis record persisted successfully",
            request_id=request_id,
            analysis_id=request_id,
            component="PERSISTENCE",
        )
    except Exception as e:
        # Failure isolation: DB error does not fail analysis or alter risk score
        result.analysis_metadata["persistence_status"] = "failed"
        result.analysis_metadata["persistence_error"] = str(e)
        metrics_collector.record_persistence(success=False)
        log_event(
            logger,
            40, # ERROR
            f"Analysis record persistence failed: {str(e)}",
            request_id=request_id,
            analysis_id=request_id,
            component="PERSISTENCE",
            error=str(e),
        )



@router.post(
    "/analyze",
    response_model=AnalysisApiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"model": ApiErrorResponse, "description": "Validation or Unprocessable Input Error"},
        500: {"model": ApiErrorResponse, "description": "Internal Component Error"},
    },
    summary="Analyze plain text opportunity for scam risk",
)
async def analyze_text_opportunity(
    payload: AnalyzeTextRequest,
    response: Response,
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    input_service: InputService = Depends(get_input_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    repository: AnalysisRepository = Depends(get_repository),
) -> AnalysisApiResponse:
    """Intake plain text opportunity, execute full ScamCheck intelligence analysis, and persist record."""
    req_id = extract_or_generate_request_id(
        header_id=x_request_id or x_correlation_id,
        payload_id=payload.request_id,
    )
    response.headers["X-Request-ID"] = req_id

    try:
        # Ingestion & Normalization
        normalized_input: OpportunityInput = input_service.process_text(
            text=payload.text,
            metadata=payload.metadata,
        )

        # Full Analysis Orchestration
        result: AnalysisResult = analysis_service.analyze(normalized_input)
        result.opportunity_id = req_id
        result.analysis_metadata["request_id"] = req_id

        # Safe Persistence
        _save_record_safely(repository, req_id, result)

        return AnalysisApiResponse(
            request_id=req_id,
            status=result.status,
            source_type=result.source_type,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            summary=result.summary,
            student_guidance=result.student_guidance,
            reasons=result.reasons,
            signals=result.signals,
            extracted_entities=result.extracted_entities,
            evidence=result.evidence,
            analysis_metadata=result.analysis_metadata,
            created_at=result.created_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "INVALID_INPUT", "message": str(e), "request_id": req_id},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred during analysis.", "request_id": req_id},
        )


@router.post(
    "/analyze/file",
    response_model=AnalysisApiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"model": ApiErrorResponse, "description": "Validation or Unprocessable File Error"},
        500: {"model": ApiErrorResponse, "description": "Internal Component Error"},
    },
    summary="Analyze uploaded image screenshot or PDF document for scam risk",
)
async def analyze_file_opportunity(
    response: Response,
    file: UploadFile = File(..., description="Image (.png, .jpg, .jpeg, .webp) or PDF (.pdf) document"),
    x_request_id: Optional[str] = Header(default=None, alias="X-Request-ID"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    input_service: InputService = Depends(get_input_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    repository: AnalysisRepository = Depends(get_repository),
) -> AnalysisApiResponse:
    """Intake uploaded image/PDF file, execute full ScamCheck intelligence analysis, and persist record."""
    req_id = extract_or_generate_request_id(header_id=x_request_id or x_correlation_id)
    response.headers["X-Request-ID"] = req_id

    # Path traversal protection: extract pure base filename
    raw_filename = file.filename or "uploaded_document"
    clean_filename = Path(raw_filename).name

    try:
        content = await file.read()
        if not content:
            raise ValueError("Uploaded file is empty (0 bytes).")

        # Ingestion & Extraction
        normalized_input: OpportunityInput = input_service.process_file(
            content=content,
            filename=clean_filename,
            mime_type=file.content_type,
        )

        # Full Analysis Orchestration
        result: AnalysisResult = analysis_service.analyze(normalized_input)
        result.opportunity_id = req_id
        result.analysis_metadata["request_id"] = req_id

        # Safe Persistence
        _save_record_safely(repository, req_id, result)

        return AnalysisApiResponse(
            request_id=req_id,
            status=result.status,
            source_type=result.source_type,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            summary=result.summary,
            student_guidance=result.student_guidance,
            reasons=result.reasons,
            signals=result.signals,
            extracted_entities=result.extracted_entities,
            evidence=result.evidence,
            analysis_metadata=result.analysis_metadata,
            created_at=result.created_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error_code": "UNPROCESSABLE_FILE", "message": str(e), "request_id": req_id},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred during file analysis.", "request_id": req_id},
        )


@router.get(
    "/analyses",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List recent analysis history records with pagination",
)
async def list_analyses(
    limit: int = Query(default=20, ge=1, le=100, description="Page limit (max 100)."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    source_type: Optional[str] = Query(default=None, description="Optional filter by source type ('text', 'image', 'pdf')."),
    risk_level: Optional[str] = Query(default=None, description="Optional filter by risk level ('low', 'medium', 'high', 'critical')."),
    repository: AnalysisRepository = Depends(get_repository),
) -> AnalysisListResponse:
    """Fetch paginated summary list of previously analyzed opportunities."""
    items, total = repository.list_recent(
        limit=limit,
        offset=offset,
        source_type=source_type,
        risk_level=risk_level,
    )
    return AnalysisListResponse(
        total=total,
        items=items,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisApiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ApiErrorResponse, "description": "Analysis Record Not Found"},
    },
    summary="Retrieve full detailed analysis record by analysis ID",
)
async def get_analysis_by_id(
    analysis_id: str,
    repository: AnalysisRepository = Depends(get_repository),
) -> AnalysisApiResponse:
    """Fetch full detailed analysis record by analysis ID."""
    clean_id = (analysis_id or "").strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": "Analysis ID cannot be empty.", "request_id": analysis_id},
        )

    record = repository.get_by_id(clean_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Analysis with ID '{clean_id}' was not found.", "request_id": clean_id},
        )

    return AnalysisApiResponse(
        request_id=record.request_id,
        status=record.status,
        source_type=record.source_type,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        summary=record.summary,
        student_guidance=record.student_guidance,
        reasons=record.reasons,
        signals=record.signals,
        extracted_entities=record.extracted_entities,
        evidence=record.evidence,
        analysis_metadata=record.analysis_metadata,
        created_at=record.created_at,
    )


@router.get(
    "/health",
    response_model=ApiHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Fast liveness health check",
)
async def api_health() -> ApiHealthResponse:
    """Instant offline liveness check for monitoring probes without network dependencies."""
    return ApiHealthResponse(
        status="healthy",
        service="ScamCheck API",
        version="1.0.0",
        stage="production_ready",
    )


from backend.app.persistence.database import get_db_manager


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness health check verifying local application and database availability",
)
async def api_readiness(response: Response) -> dict:
    """Readiness probe verifying local database availability without external network calls."""
    db_ok = get_db_manager().check_readiness()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "database": "unavailable",
            "service": "ScamCheck API",
        }
    return {
        "status": "ready",
        "database": "healthy",
        "service": "ScamCheck API",
    }

