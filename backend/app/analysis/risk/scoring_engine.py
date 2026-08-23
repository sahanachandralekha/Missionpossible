"""Deterministic Risk Scoring Engine for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 8)

Purpose:
Aggregates and synthesizes detected RiskSignal objects into a calibrated 0-100
opportunity risk score, assigns the corresponding RiskLevel band (LOW, MEDIUM, HIGH, CRITICAL),
and produces an explainable AnalysisResult with reasons, evidence, and student safety guidance.

Architectural Invariants:
- Consumes ONLY RiskSignal objects (does NOT perform regex extraction itself).
- Zero ML / LLM dependencies.
- Zero network / external API lookups.
- Deterministic: Identical signals always produce the identical score and level.
"""

from typing import Any, Dict, List, Optional, Set
from backend.app.schemas.opportunity import ProcessingStatus, SourceType
from backend.app.analysis.models.analysis_context import AnalysisContext
from backend.app.analysis.models.analysis_result import AnalysisResult
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.enums import AnalysisStatus, RiskLevel
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.analysis.risk.score_policy import (
    DEFAULT_BASE_WEIGHT,
    RULE_WEIGHTS,
    SEVERITY_MULTIPLIERS,
    STUDENT_GUIDANCE_MAP,
    SUMMARY_MAP,
    get_risk_level,
)


class RiskScoringEngine:
    """Deterministic opportunity-risk scoring engine."""

    def score(
        self,
        context: AnalysisContext,
        signals: Optional[List[RiskSignal]] = None,
    ) -> AnalysisResult:
        """Compute the final risk score and complete AnalysisResult from an AnalysisContext.
        
        Args:
            context: Analysis envelope containing OpportunityInput, ExtractedEntities, etc.
            signals: Optional pre-filtered RiskSignal list. If None, uses empty or provided list.
            
        Returns:
            Fully populated AnalysisResult with score, level, reasons, guidance, and evidence.
        """
        source_type = SourceType.TEXT
        if context.opportunity and context.opportunity.source_type:
            source_type = context.opportunity.source_type

        # Check for technical ingestion/processing failures
        is_processing_failure = False
        if context.status == AnalysisStatus.FAILED:
            is_processing_failure = True
        elif context.opportunity and context.opportunity.processing_status == ProcessingStatus.FAILED:
            is_processing_failure = True

        result_status = AnalysisStatus.FAILED if is_processing_failure else AnalysisStatus.COMPLETED

        # Collect entities & evidence from context
        entities = context.extracted_entities or ExtractedEntities()
        evidence_pool = list(context.evidence_pool or [])

        # If signals contain additional evidence, merge into evidence_pool
        active_signals = signals or []
        for s in active_signals:
            for ev in s.evidence:
                if not any(e.value == ev.value and e.location == ev.location for e in evidence_pool):
                    evidence_pool.append(ev)

        return self.score_signals(
            signals=active_signals,
            source_type=source_type,
            entities=entities,
            evidence=evidence_pool,
            status=result_status,
        )

    def score_signals(
        self,
        signals: List[RiskSignal],
        source_type: SourceType = SourceType.TEXT,
        entities: Optional[ExtractedEntities] = None,
        evidence: Optional[List[Evidence]] = None,
        status: AnalysisStatus = AnalysisStatus.COMPLETED,
    ) -> AnalysisResult:
        """Core scoring synthesis from a list of RiskSignal objects."""
        if not signals:
            return AnalysisResult(
                source_type=source_type,
                risk_score=0,
                risk_level=RiskLevel.LOW,
                signals=[],
                extracted_entities=entities or ExtractedEntities(),
                evidence=evidence or [],
                summary=SUMMARY_MAP[RiskLevel.LOW],
                student_guidance=STUDENT_GUIDANCE_MAP[RiskLevel.LOW],
                reasons=[],
                status=status,
                analysis_metadata={
                    "scoring_engine": "deterministic-v1",
                    "signal_contributions": [],
                    "raw_score": 0.0,
                    "final_score": 0,
                    "compound_adjustment": 0.0,
                },
            )

        # 1. Defensively deduplicate by signal_id
        seen_signal_ids: Set[str] = set()
        unique_signals: List[RiskSignal] = []
        for sig in signals:
            if sig.signal_id not in seen_signal_ids:
                seen_signal_ids.add(sig.signal_id)
                unique_signals.append(sig)

        # 2. Calculate individual signal contributions
        raw_score: float = 0.0
        signal_contributions: List[Dict[str, Any]] = []
        compound_adjustment: float = 0.0

        for sig in unique_signals:
            base_weight = RULE_WEIGHTS.get(sig.signal_id, DEFAULT_BASE_WEIGHT)
            sev_multiplier = SEVERITY_MULTIPLIERS.get(sig.severity, 1.0)
            conf = max(0.0, min(1.0, float(sig.confidence)))

            if sig.signal_id == "SIG_MULTIPLE_HIGH_RISK_PATTERNS":
                # Special compound adjustment
                contribution = round(base_weight * sev_multiplier * conf, 1)
                compound_adjustment = contribution
            else:
                contribution = round(base_weight * sev_multiplier * conf, 1)

            sig.score_contribution = contribution
            raw_score += contribution

            signal_contributions.append({
                "signal_id": sig.signal_id,
                "title": sig.title,
                "base_weight": base_weight,
                "severity_multiplier": sev_multiplier,
                "confidence": conf,
                "contribution": contribution,
            })

        # 3. Clamp final numerical score to [0, 100]
        clamped_score = int(round(max(0.0, min(100.0, raw_score))))

        # 4. Determine calibrated RiskLevel band
        risk_level = get_risk_level(clamped_score)

        # 5. Build human-readable reasons from unique signals
        reasons: List[str] = []
        for sig in unique_signals:
            reason_text = sig.title
            if reason_text and reason_text not in reasons:
                reasons.append(reason_text)

        # 6. Assemble AnalysisResult
        return AnalysisResult(
            source_type=source_type,
            risk_score=clamped_score,
            risk_level=risk_level,
            signals=unique_signals,
            extracted_entities=entities or ExtractedEntities(),
            evidence=evidence or [],
            summary=SUMMARY_MAP[risk_level],
            student_guidance=STUDENT_GUIDANCE_MAP[risk_level],
            reasons=reasons,
            status=status,
            analysis_metadata={
                "scoring_engine": "deterministic-v1",
                "signal_contributions": signal_contributions,
                "raw_score": raw_score,
                "final_score": clamped_score,
                "compound_adjustment": compound_adjustment,
            },
        )
