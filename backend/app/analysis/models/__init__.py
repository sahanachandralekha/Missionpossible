"""Common analysis data contracts and schema definitions for ScamCheck."""

from backend.app.analysis.models.analysis_context import AnalysisContext
from backend.app.analysis.models.analysis_result import AnalysisResult
from backend.app.analysis.models.entities import (
    ContactInfoEntity,
    DateEntity,
    EmailEntity,
    ExtractedEntities,
    JobTitleEntity,
    LocationEntity,
    MonetaryAmountEntity,
    OrganizationEntity,
    PaymentDetailEntity,
    PercentageEntity,
    PhoneEntity,
    UrlEntity,
)
from backend.app.analysis.models.enums import (
    AnalysisStatus,
    RiskLevel,
    SignalSeverity,
)
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal

__all__ = [
    "AnalysisContext",
    "AnalysisResult",
    "AnalysisStatus",
    "ContactInfoEntity",
    "DateEntity",
    "EmailEntity",
    "Evidence",
    "ExtractedEntities",
    "JobTitleEntity",
    "LocationEntity",
    "MonetaryAmountEntity",
    "OrganizationEntity",
    "PaymentDetailEntity",
    "PercentageEntity",
    "PhoneEntity",
    "RiskLevel",
    "RiskSignal",
    "SignalSeverity",
    "UrlEntity",
]
