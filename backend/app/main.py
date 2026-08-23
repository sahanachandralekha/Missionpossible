"""ScamCheck FastAPI Application Entrypoint.

Provides the REST API foundation for the ScamCheck opportunity-risk assessment system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.routes.analysis import router as analysis_router
from backend.app.schemas.opportunity import HealthResponse

app = FastAPI(
    title="ScamCheck API",
    description=(
        "Opportunity-risk assessment foundation for students evaluating "
        "internships, jobs, gigs, and scholarships across text, images, and PDFs."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hackathon development setting; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(analysis_router)


@app.get(
    "/",
    response_model=HealthResponse,
    tags=["Health & Status"],
    summary="Root service health check",
)
async def root() -> HealthResponse:
    """Service status and stage acknowledgment."""
    return HealthResponse(
        status="healthy",
        service="ScamCheck API",
        version="0.1.0",
        stage="foundation",
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health & Status"],
    summary="Liveness / Readiness health probe",
)
async def health_check() -> HealthResponse:
    """Health check endpoint for orchestrators and monitoring."""
    return HealthResponse(
        status="healthy",
        service="ScamCheck API",
        version="0.1.0",
        stage="foundation",
    )
