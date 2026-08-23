"""Unified Analysis Orchestration Service for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 9)

Connects all deterministic analysis components:
OpportunityInput -> AnalysisContext -> EntityExtractor -> RuleBasedSignalEngine -> RiskScoringEngine -> AnalysisResult
"""

from typing import Optional
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


class AnalysisService:
    """Unified Orchestrator for ScamCheck opportunity analysis.
    
    Coordinates the execution of deterministic analysis components in strict sequence:
    1. Opportunity validation and AnalysisContext initialization
    2. Factual Entity Extraction (EntityExtractor)
    3. Rule-Based Scam Signal Detection (RuleBasedSignalEngine)
    4. Deterministic Risk Scoring & Policy Synthesis (RiskScoringEngine)
    5. Assembly of the final comprehensive AnalysisResult
    """

    def __init__(
        self,
        entity_extractor: Optional[EntityExtractor] = None,
        signal_engine: Optional[RuleBasedSignalEngine] = None,
        scoring_engine: Optional[RiskScoringEngine] = None,
    ) -> None:
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.signal_engine = signal_engine or RuleBasedSignalEngine()
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
            detected_signals = self.signal_engine.detect(context)

            # 3. Risk Scoring & Synthesis
            result = self.scoring_engine.score(context, signals=detected_signals)
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
                "risk_scoring": "completed",
                "total_entities_extracted": total_entities,
                "total_signals_detected": len(detected_signals),
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
