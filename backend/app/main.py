"""ScamCheck FastAPI Application Entrypoint.

STATUS: FULLY IMPLEMENTED & HARDENED (Part 16)

Provides the production-ready REST API foundation for ScamCheck opportunity-risk assessment.
Includes:
- Centralized configuration settings
- Structured application logging
- Request correlation & timing middleware
- Production security headers
- Configurable CORS policy
- Liveness & readiness probes
- Diagnostic operational metrics
"""

from typing import Dict, Any
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.router import api_router
from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging, get_logger
from backend.app.core.middleware import RequestCorrelationMiddleware, SecurityHeadersMiddleware
from backend.app.core.metrics import metrics_collector
from backend.app.persistence.database import get_db_manager
from backend.app.schemas.opportunity import HealthResponse

# Initialize logging on startup
setup_logging()
logger = get_logger("main")
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Opportunity-risk assessment foundation for students evaluating "
        "internships, jobs, gigs, and scholarships across text, images, and PDFs."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Attach Request Correlation & Latency Middleware
app.add_middleware(RequestCorrelationMiddleware)

# Configurable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Include API Routers (/api/v1)
app.include_router(api_router)


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
        service=settings.app_name,
        version="1.0.0",
        stage="foundation",

    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health & Status"],
    summary="Fast liveness health probe",
)
async def health_check() -> HealthResponse:
    """Fast, zero-network liveness check for orchestrator probes."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version="1.0.0",
        stage="production_ready",
    )


@app.get(
    "/ready",
    tags=["Health & Status"],
    summary="Readiness health probe for load balancers",
)
async def readiness_check(response: Response) -> Dict[str, Any]:
    """Readiness probe verifying local application and database availability without external network calls."""
    db_ok = get_db_manager().check_readiness()
    if not db_ok:
        response.status_code = status.HTTP_537_STATUS_CODE if hasattr(status, "HTTP_537_STATUS_CODE") else 503
        return {
            "status": "unready",
            "database": "unavailable",
            "service": settings.app_name,
        }
    return {
        "status": "ready",
        "database": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get(
    "/metrics",
    tags=["Health & Status"],
    summary="Operational telemetry diagnostic snapshot",
)
async def metrics_endpoint() -> Dict[str, Any]:
    """Retrieve operational telemetry timing and request counters."""
    return metrics_collector.get_summary()
