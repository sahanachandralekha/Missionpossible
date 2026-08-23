"""Analysis Layer for ScamCheck.

STATUS: DATA CONTRACTS IMPLEMENTED (Common Analysis Schemas)

This package contains the data contracts and analytical interfaces for ScamCheck:
- Common schemas (analysis/models/): AnalysisResult, RiskSignal, Evidence, ExtractedEntities, AnalysisContext
- ML classification placeholder (analysis/ml/)
- Risk engine placeholder (analysis/risk/)

Flow:
OpportunityInput -> AnalysisContext -> ExtractedEntities -> RiskSignals -> RiskScoring -> AnalysisResult
"""

from backend.app.analysis.extraction import EntityExtractor
from backend.app.analysis.rules import RuleBasedSignalEngine
from backend.app.analysis.risk import RiskScoringEngine, get_risk_level
from backend.app.analysis.url import UrlAnalyzer
from backend.app.analysis.ml import SemanticAnalyzer
from backend.app.analysis.domain import DomainVerifier
from backend.app.analysis.analysis_service import AnalysisService
from backend.app.analysis.models import (
    AnalysisContext,
    AnalysisResult,
    AnalysisStatus,
    ContactInfoEntity,
    DateEntity,
    EmailEntity,
    Evidence,
    ExtractedEntities,
    JobTitleEntity,
    LocationEntity,
    MonetaryAmountEntity,
    OrganizationEntity,
    PaymentDetailEntity,
    PercentageEntity,
    PhoneEntity,
    RiskLevel,
    RiskSignal,
    SignalSeverity,
    UrlEntity,
)

__all__ = [
    "AnalysisContext",
    "AnalysisResult",
    "AnalysisService",
    "AnalysisStatus",
    "ContactInfoEntity",
    "DateEntity",
    "DomainVerifier",
    "EmailEntity",
    "EntityExtractor",
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
    "RiskScoringEngine",
    "RiskSignal",
    "RuleBasedSignalEngine",
    "SemanticAnalyzer",
    "SignalSeverity",
    "UrlAnalyzer",
    "UrlEntity",
    "get_risk_level",
]







