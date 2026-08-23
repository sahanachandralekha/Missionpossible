"""Unified Analysis Orchestration Service for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 12)

Connects all deterministic, semantic, and domain verification analysis components:
OpportunityInput -> AnalysisContext -> EntityExtractor -> RuleBasedSignalEngine -> UrlAnalyzer -> SemanticAnalyzer -> DomainVerifier -> RiskScoringEngine -> AnalysisResult
"""

from typing import Any, Dict, List, Optional
from backend.app.schemas.opportunity import OpportunityInput, ProcessingStatus, SourceType
from backend.app.analysis.models import (
    AnalysisContext,
    AnalysisResult,
    AnalysisStatus,
    ExtractedEntities,
    RiskLevel,
    RiskSignal,
)
from backend.app.analysis.extraction import EntityExtractor
from backend.app.analysis.rules import RuleBasedSignalEngine
from backend.app.analysis.risk import RiskScoringEngine
from backend.app.analysis.url import UrlAnalyzer
from backend.app.analysis.ml import SemanticAnalyzer
from backend.app.analysis.domain import DomainVerifier


class AnalysisService:
    """Unified Orchestrator for ScamCheck opportunity analysis.
    
    Coordinates the execution of deterministic, semantic, and domain verification components in strict sequence:
    1. Opportunity validation and AnalysisContext initialization
    2. Factual Entity Extraction (EntityExtractor)
    3. Rule-Based Scam Signal Detection (RuleBasedSignalEngine)
    4. URL & Domain Structure Intelligence (UrlAnalyzer)
    5. Contextual ML/LLM Semantic Intelligence (SemanticAnalyzer)
    6. External Domain Verification & Identity Intelligence (DomainVerifier)
    7. Deterministic Risk Scoring & Policy Synthesis (RiskScoringEngine)
    8. Assembly of the final comprehensive AnalysisResult
    """

    def __init__(
        self,
        entity_extractor: Optional[EntityExtractor] = None,
        signal_engine: Optional[RuleBasedSignalEngine] = None,
        url_analyzer: Optional[UrlAnalyzer] = None,
        semantic_analyzer: Optional[SemanticAnalyzer] = None,
        domain_verifier: Optional[DomainVerifier] = None,
        scoring_engine: Optional[RiskScoringEngine] = None,
    ) -> None:
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.signal_engine = signal_engine or RuleBasedSignalEngine()
        self.url_analyzer = url_analyzer or UrlAnalyzer()
        self.semantic_analyzer = semantic_analyzer or SemanticAnalyzer()
        self.domain_verifier = domain_verifier or DomainVerifier()
        self.scoring_engine = scoring_engine or RiskScoringEngine()

    def analyze(self, opportunity_input: OpportunityInput) -> AnalysisResult:
        """Run the complete end-to-end analytical pipeline on a normalized opportunity.
        
        Args:
            opportunity_input: Validated OpportunityInput from any supported modality (Text, Image, PDF).
            
        Returns:
            AnalysisResult: Fully synthesized result containing score, risk level, reasons, evidence, and guidance.
        """
        if opportunity_input is None:
            raise ValueError("OpportunityInput cannot be None.")

        source_type = opportunity_input.source_type or SourceType.TEXT
        source_str = source_type.value if hasattr(source_type, "value") else str(source_type)
        text = (opportunity_input.extracted_text or "").strip()

        # Handle upstream ingestion failure gracefully
        if opportunity_input.processing_status == ProcessingStatus.FAILED:
            context = AnalysisContext(
                opportunity=opportunity_input,
                status=AnalysisStatus.FAILED,
                error_message="Upstream ingestion failed before analysis.",
            )
            result = self.scoring_engine.score(context, signals=[])
            result.status = AnalysisStatus.FAILED
            result.analysis_metadata.update({
                "orchestrator": "AnalysisService",
                "pipeline_version": "1.0",
                "source_type": source_str,
                "ingestion_status": "failed",
                "entity_extraction": "skipped",
                "rule_detection": "skipped",
                "url_analysis": "skipped",
                "semantic_analysis": {"enabled": False, "status": "skipped"},
                "domain_verification": {"enabled": False, "status": "skipped"},
                "risk_scoring": "completed",
            })
            return result

        # Handle empty/whitespace input
        if not text:
            context = AnalysisContext(
                opportunity=opportunity_input,
                status=AnalysisStatus.COMPLETED,
            )
            result = self.scoring_engine.score(context, signals=[])
            result.analysis_metadata.update({
                "orchestrator": "AnalysisService",
                "pipeline_version": "1.0",
                "source_type": source_str,
                "entity_extraction": "completed",
                "rule_detection": "completed",
                "url_analysis": "completed",
                "semantic_analysis": {"enabled": True, "provider": self.semantic_analyzer.get_provider_name(), "signals_generated": 0, "status": "completed"},
                "domain_verification": {"enabled": True, "provider": self.domain_verifier.get_provider_name(), "domains_checked": [], "signals_generated": 0, "status": "completed"},
                "risk_scoring": "completed",
            })
            return result

        # Initialize AnalysisContext in PROCESSING state
        context = AnalysisContext(
            opportunity=opportunity_input,
            status=AnalysisStatus.PROCESSING,
        )

        try:
            # 1. Entity Extraction
            extracted_entities, evidence_pool = self.entity_extractor.extract_from_text(
                text=opportunity_input.extracted_text,
                source=source_str,
            )
            context.extracted_entities = extracted_entities
            context.evidence_pool = evidence_pool

            # 2. Rule-Based Scam Signal Detection
            rule_signals = self.signal_engine.detect(context)

            # 3. URL & Domain Structure Intelligence
            url_signals: List[RiskSignal] = []
            if extracted_entities.urls:
                url_signals = self.url_analyzer.analyze(context)

            # 4. Contextual Semantic Analysis (with failure isolation)
            semantic_signals: List[RiskSignal] = []
            semantic_meta: Dict[str, Any] = {
                "enabled": True,
                "provider": self.semantic_analyzer.get_provider_name(),
                "signals_generated": 0,
                "status": "completed",
            }
            try:
                deterministic_signals = rule_signals + url_signals
                semantic_signals = self.semantic_analyzer.analyze(
                    context=context,
                    existing_signals=deterministic_signals,
                )
                if getattr(self.semantic_analyzer, "last_status", None) == "failed":
                    semantic_meta["status"] = "failed"
                    semantic_meta["error"] = "provider_unavailable"
                else:
                    semantic_meta["signals_generated"] = len(semantic_signals)
            except Exception:
                semantic_meta["status"] = "failed"
                semantic_meta["error"] = "provider_unavailable"

            # 5. External Domain Verification & Identity Intelligence (with failure isolation)
            domain_signals: List[RiskSignal] = []
            domain_meta: Dict[str, Any] = {
                "enabled": True,
                "provider": self.domain_verifier.get_provider_name(),
                "domains_checked": [],
                "signals_generated": 0,
                "status": "completed",
            }
            if extracted_entities.urls:
                try:
                    domain_signals = self.domain_verifier.verify(context)
                    domain_meta["domains_checked"] = getattr(self.domain_verifier, "last_checked_domains", [])
                    if getattr(self.domain_verifier, "last_status", None) == "failed":
                        domain_meta["status"] = "failed"
                        domain_meta["error"] = "provider_unavailable"
                    else:
                        domain_meta["signals_generated"] = len(domain_signals)
                except Exception:
                    domain_meta["status"] = "failed"
                    domain_meta["error"] = "provider_unavailable"

            # Combine all analytical signals
            all_signals = rule_signals + url_signals + semantic_signals + domain_signals

            # 6. Risk Scoring & Synthesis (Single authority: RiskScoringEngine)
            result = self.scoring_engine.score(context, signals=all_signals)
            result.status = AnalysisStatus.COMPLETED

            # Add orchestrator metadata
            total_entities = (
                len(extracted_entities.organizations)
                + len(extracted_entities.job_titles)
                + len(extracted_entities.emails)
                + len(extracted_entities.phone_numbers)
                + len(extracted_entities.urls)
                + len(extracted_entities.monetary_amounts)
                + len(extracted_entities.percentages)
                + len(extracted_entities.dates)
                + len(extracted_entities.locations)
                + len(extracted_entities.payment_details)
            )
            result.analysis_metadata.update({
                "orchestrator": "AnalysisService",
                "pipeline_version": "1.0",
                "source_type": source_str,
                "entity_extraction": "completed",
                "rule_detection": "completed",
                "url_analysis": "completed",
                "semantic_analysis": semantic_meta,
                "domain_verification": domain_meta,
                "risk_scoring": "completed",
                "total_entities_extracted": total_entities,
                "total_signals_detected": len(all_signals),
                "rule_signals_count": len(rule_signals),
                "url_signals_count": len(url_signals),
                "semantic_signals_count": len(semantic_signals),
                "domain_signals_count": len(domain_signals),
            })

            return result

        except Exception as e:
            context.status = AnalysisStatus.FAILED
            context.error_message = str(e)
            result = self.scoring_engine.score(context, signals=[])
            result.status = AnalysisStatus.FAILED
            result.analysis_metadata.update({
                "orchestrator": "AnalysisService",
                "pipeline_version": "1.0",
                "error": str(e),
            })
            return result
