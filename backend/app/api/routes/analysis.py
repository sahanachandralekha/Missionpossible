"""Analysis API Routes Foundation.

STATUS: API Routing Foundation IMPLEMENTED.
(Risk scoring and ML evaluation are intentionally not implemented in this phase.)

This module provides intake endpoints that pass incoming requests to the InputService
to yield a normalized OpportunityInput model.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from backend.app.schemas.opportunity import (
    AnalysisResponsePlaceholder,
    OpportunityInput,
    TextSubmissionRequest,
)
from backend.app.services.input_service import InputService

router = APIRouter(prefix="/api/analyze", tags=["Analysis Foundation"])


def get_input_service() -> InputService:
    """Dependency injector for InputService."""
    return InputService()


@router.post(
    "/text",
    response_model=AnalysisResponsePlaceholder,
    status_code=status.HTTP_200_OK,
    summary="Submit plain text opportunity for normalization and future analysis",
)
async def analyze_text(
    payload: TextSubmissionRequest,
    input_service: InputService = Depends(get_input_service),
) -> AnalysisResponsePlaceholder:
    """Intake endpoint for raw text opportunities (e.g. WhatsApp message, email, job post)."""
    try:
        normalized_input: OpportunityInput = input_service.process_text(
            text=payload.text,
            metadata=payload.metadata,
        )
        return AnalysisResponsePlaceholder(
            status="success",
            message="Text opportunity normalized successfully.",
            normalized_input=normalized_input,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post(
    "/file",
    response_model=AnalysisResponsePlaceholder,
    status_code=status.HTTP_200_OK,
    summary="Upload image or PDF document opportunity for normalization and future analysis",
)
async def analyze_file(
    file: UploadFile = File(..., description="Image (.png, .jpg, .jpeg, .webp) or PDF (.pdf) file"),
    input_service: InputService = Depends(get_input_service),
) -> AnalysisResponsePlaceholder:
    """Intake endpoint for uploaded opportunity documents (screenshots, photos, offer PDFs)."""
    try:
        content = await file.read()
        normalized_input: OpportunityInput = input_service.process_file(
            content=content,
            filename=file.filename,
            mime_type=file.content_type,
        )
        return AnalysisResponsePlaceholder(
            status="success",
            message=f"File '{file.filename}' processed into normalized opportunity format.",
            normalized_input=normalized_input,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
