"""Centralized Runtime Application Configuration for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 16)

Centralizes configuration settings across backend environments with safe defaults.
Reads environment variables (prefixed with SCAMCHECK_ or standard names).
NOTE: Never hardcodes production secrets or exposes sensitive settings via API endpoints.
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Centralized runtime application settings schema."""

    # Application Identification
    app_name: str = Field(default="ScamCheck API", description="Service application name.")
    environment: str = Field(default="development", description="Deployment environment (development, staging, production, test).")
    debug: bool = Field(default=False, description="Debug mode flag.")

    # Server Address & Binding
    api_host: str = Field(default="0.0.0.0", description="API host interface binding.")
    api_port: int = Field(default=8000, description="API port binding.")

    # Persistence Configuration
    database_path: str = Field(default="scamcheck.db", description="SQLite database file path or :memory: for testing.")
    enable_persistence: bool = Field(default=True, description="Enable automatic analysis record persistence.")

    # Intelligence & Provider Modes
    domain_provider_mode: str = Field(default="offline", description="Domain verification provider ('offline', 'network', 'mock').")
    semantic_provider_mode: str = Field(default="deterministic", description="Semantic ML provider ('deterministic', 'mock').")

    # Upload & Processing Boundaries
    max_text_length: int = Field(default=100_000, description="Maximum permitted text length in characters.")
    max_image_size_bytes: int = Field(default=10 * 1024 * 1024, description="Maximum image upload size in bytes (10 MB).")
    max_pdf_size_bytes: int = Field(default=15 * 1024 * 1024, description="Maximum PDF upload size in bytes (15 MB).")

    # Security & CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origin URLs.",
    )

    # Logging & Diagnostics
    log_level: str = Field(default="INFO", description="Application logging level (DEBUG, INFO, WARNING, ERROR).")
    frontend_api_base_url: str = Field(default="http://localhost:8000", description="Client API base URL configuration.")

    @classmethod
    def load_from_env(cls) -> "Settings":
        """Construct Settings instance from environment variables with safe defaults."""
        env_name = os.getenv("SCAMCHECK_ENV", os.getenv("ENVIRONMENT", "development")).lower()
        debug_val = os.getenv("SCAMCHECK_DEBUG", os.getenv("DEBUG", "false")).lower() in ("true", "1", "yes")

        host = os.getenv("SCAMCHECK_HOST", os.getenv("API_HOST", "0.0.0.0"))
        port = int(os.getenv("SCAMCHECK_PORT", os.getenv("API_PORT", "8000")))

        db_path = os.getenv("SCAMCHECK_DB_PATH", os.getenv("DATABASE_PATH", "scamcheck.db"))
        enable_pers = os.getenv("SCAMCHECK_ENABLE_PERSISTENCE", "true").lower() in ("true", "1", "yes")

        domain_mode = os.getenv("SCAMCHECK_DOMAIN_PROVIDER", os.getenv("DOMAIN_PROVIDER_MODE", "offline")).lower()
        semantic_mode = os.getenv("SCAMCHECK_SEMANTIC_PROVIDER", os.getenv("SEMANTIC_PROVIDER_MODE", "deterministic")).lower()

        # Parse CORS origins
        raw_cors = os.getenv("CORS_ORIGINS", "")
        if raw_cors:
            origins = [o.strip() for o in raw_cors.split(",") if o.strip()]
        else:
            if env_name == "production":
                origins = ["http://localhost:3000"]  # Restrictive production default
            else:
                origins = [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ]

        log_lvl = os.getenv("SCAMCHECK_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
        frontend_url = os.getenv("VITE_API_BASE_URL", os.getenv("FRONTEND_API_BASE_URL", "http://localhost:8000"))

        return cls(
            app_name="ScamCheck API",
            environment=env_name,
            debug=debug_val,
            api_host=host,
            api_port=port,
            database_path=db_path,
            enable_persistence=enable_pers,
            domain_provider_mode=domain_mode,
            semantic_provider_mode=semantic_mode,
            cors_origins=origins,
            log_level=log_lvl,
            frontend_api_base_url=frontend_url,
        )


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global cached Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings.load_from_env()
    return _settings_instance


def reset_settings() -> None:
    """Clear cached Settings instance (used in unit tests)."""
    global _settings_instance
    _settings_instance = None
