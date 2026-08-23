"""URL & Domain Structure Intelligence Module for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 10)

Exports:
- UrlAnalyzer
- URL_SIGNAL_SPECS
- KNOWN_SHORTENERS
- GENERIC_JOB_PLATFORMS
"""

from backend.app.analysis.url.url_analyzer import UrlAnalyzer
from backend.app.analysis.url.url_rules import (
    GENERIC_JOB_PLATFORMS,
    KNOWN_SHORTENERS,
    URL_SIGNAL_SPECS,
)

__all__ = [
    "GENERIC_JOB_PLATFORMS",
    "KNOWN_SHORTENERS",
    "URL_SIGNAL_SPECS",
    "UrlAnalyzer",
]
