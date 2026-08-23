"""ScamCheck Core Package.

STATUS: FULLY IMPLEMENTED (Part 16)

Provides centralized application configuration, structured logging, request correlation middleware, metrics collection, and security headers.
"""

from backend.app.core.config import Settings, get_settings, reset_settings

__all__ = ["Settings", "get_settings", "reset_settings"]
