"""Structured Application Logging & Diagnostic Telemetry for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 16)

Provides:
- Centralized logger configuration
- Structured JSON / key-value log formatter
- Correlation binding (request_id, analysis_id, component)
- Privacy enforcement: Strictly forbids logging secrets, raw file bytes, passwords, or full opportunity text.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from backend.app.core.config import get_settings


class StructuredJsonFormatter(logging.Formatter):
    """Custom logging formatter outputting clean, machine-readable JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach request correlation attributes if present on record
        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = str(record.request_id)
        if hasattr(record, "analysis_id") and record.analysis_id:
            log_data["analysis_id"] = str(record.analysis_id)
        if hasattr(record, "component") and record.component:
            log_data["component"] = str(record.component)

        # Attach extra structured metadata, sanitizing sensitive keys
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            for k, v in record.extra_fields.items():
                k_lower = k.lower()
                if any(kw in k_lower for kw in ("password", "secret", "token", "auth", "raw_bytes", "file_content", "text_payload", "key")):
                    log_data[k] = "[REDACTED_SENSITIVE_DATA]"
                else:
                    log_data[k] = v


        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure centralized application root logger."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger("scamcheck")
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str = "scamcheck") -> logging.Logger:
    """Get a logger instance prefixed with scamcheck."""
    if not name.startswith("scamcheck"):
        full_name = f"scamcheck.{name}"
    else:
        full_name = name
    return logging.getLogger(full_name)


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    request_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    component: Optional[str] = None,
    **extra_fields: Any,
) -> None:
    """Safely log a structured event with correlation attributes and privacy sanitization."""
    # Sanitize sensitive fields before passing to logger
    sanitized: Dict[str, Any] = {}
    for k, v in extra_fields.items():
        if any(secret_kw in k.lower() for secret_kw in ("password", "secret", "token", "key", "auth")):
            sanitized[k] = "[REDACTED_SECRET]"
        elif k in ("raw_bytes", "content", "file_bytes", "full_text"):
            sanitized[k] = f"[{type(v).__name__} length={len(v) if hasattr(v, '__len__') else 'N/A'}]"
        else:
            sanitized[k] = v

    extra = {
        "request_id": request_id,
        "analysis_id": analysis_id,
        "component": component,
        "extra_fields": sanitized,
    }
    logger.log(level, message, extra=extra)
