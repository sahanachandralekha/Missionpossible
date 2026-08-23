"""Semantic Intelligence Analysis Engine for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 11)

Coordinates semantic contextual opportunity analysis:
- Invokes configured SemanticModelProvider behind an abstract interface
- Binds detections to unified RiskSignal & Evidence models
- Defensively validates and clamps confidence scores (0.0 <= confidence <= 1.0)
- Applies intelligent deduplication to prevent double-counting deterministic rule signals
- Ensures strict failure isolation (technical provider failure != scam risk)
- Strictly enforces score_contribution = 0.0 (RiskScoringEngine remains single scoring authority)
"""

from typing import Dict, List, Optional, Set
from backend.app.schemas.opportunity import SourceType
from backend.app.analysis.models import (
    AnalysisContext,
    Evidence,
    RiskSignal,
    SignalSeverity,
)
from backend.app.analysis.ml.base import SemanticModelProvider
from backend.app.analysis.ml.provider import get_semantic_provider
from backend.app.analysis.ml.schemas import SemanticModelOutput, SemanticSignalItem


class SemanticAnalyzer:
    """Semantic analysis orchestrator bridging provider outputs with ScamCheck contracts."""

    def __init__(self, provider: Optional[SemanticModelProvider] = None) -> None:
        self.provider = provider or get_semantic_provider()
        self.last_status: str = "initialized"
        self.last_error: Optional[str] = None

    def get_provider_name(self) -> str:
        """Return the active provider's name."""
        return self.provider.get_provider_name()


    def analyze(
        self,
        context: AnalysisContext,
        existing_signals: Optional[List[RiskSignal]] = None,
    ) -> List[RiskSignal]:
        """Perform semantic analysis on an active AnalysisContext.
        
        Args:
            context: The active opportunity AnalysisContext.
            existing_signals: Optional list of previously detected deterministic signals for deduplication.
            
        Returns:
            List[RiskSignal]: Traceable semantic risk signals (score_contribution=0.0).
        """
        if context is None or context.opportunity is None:
            return []

        text = context.opportunity.extracted_text or ""
        source_type = context.opportunity.source_type or SourceType.TEXT
        source_str = source_type.value if hasattr(source_type, "value") else str(source_type)

        existing_signal_ids: Set[str] = set()
        if existing_signals:
            existing_signal_ids = {s.signal_id for s in existing_signals}

        return self.analyze_text(
            text=text,
            source=source_str,
            context=context,
            existing_signal_ids=existing_signal_ids,
        )

    def analyze_text(
        self,
        text: str,
        source: str = "text",
        context: Optional[AnalysisContext] = None,
        existing_signal_ids: Optional[Set[str]] = None,
    ) -> List[RiskSignal]:
        """Perform semantic analysis directly on raw text.
        
        Args:
            text: Opportunity text to analyze.
            source: Source modality string ('text', 'image', 'pdf').
            context: Optional parent AnalysisContext.
            existing_signal_ids: Set of signal IDs already detected by deterministic rules.
            
        Returns:
            List[RiskSignal]: List of semantic risk signals.
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return []

        existing_ids = existing_signal_ids or set()

        try:
            output: SemanticModelOutput = self.provider.analyze(clean_text, context=context)
            self.last_status = "completed"
            self.last_error = None
        except Exception as err:
            # Failure isolation: Provider crash must never break pipeline
            self.last_status = "failed"
            self.last_error = str(err)
            return []


        if not output.is_success or not output.signals:
            return []

        risk_signals: List[RiskSignal] = []
        seen_semantic_ids: Set[str] = set()

        for item in output.signals:
            # 1. Defensively clamp confidence to [0.0, 1.0]
            raw_conf = float(item.confidence) if item.confidence is not None else 0.75
            clamped_conf = min(max(raw_conf, 0.0), 1.0)

            # 2. Deduplication and Overlap Prevention with Deterministic Rules
            if self._is_redundant_signal(item.signal_id, existing_ids):
                continue

            if item.signal_id in seen_semantic_ids:
                # Deduplicate repeated findings from same provider run
                continue
            seen_semantic_ids.add(item.signal_id)

            # 3. Create traceable Evidence without fabricating offsets
            evidence_item = self._build_evidence(
                evidence_text=item.evidence_text,
                full_text=clean_text,
                source=source,
                signal_id=item.signal_id,
            )

            # 4. Construct RiskSignal adhering strictly to common contract
            signal = RiskSignal(
                signal_id=item.signal_id,
                signal_type="semantic",
                title=item.title,
                description=item.description,
                severity=item.severity,
                confidence=clamped_conf,
                evidence=[evidence_item],
                score_contribution=0.0,  # Single authority: RiskScoringEngine
                metadata={
                    "provider": output.provider_name,
                    "explanation": item.explanation or item.description,
                    "analysis_type": "semantic_context",
                },
            )
            risk_signals.append(signal)

        return risk_signals

    def _is_redundant_signal(self, semantic_id: str, existing_ids: Set[str]) -> bool:
        """Check if a semantic signal is completely redundant with an already fired deterministic rule."""
        if not existing_ids:
            return False

        # If rule engine already triggered explicit upfront payment, avoid double counting payment pressure
        if semantic_id == "SIG_SEMANTIC_PAYMENT_PRESSURE" and "SIG_UPFRONT_PAYMENT" in existing_ids:
            return True

        # If rule engine already triggered explicit unrealistic earnings, avoid double counting promise
        if semantic_id == "SIG_SEMANTIC_UNREALISTIC_PROMISE" and "SIG_UNREALISTIC_EARNINGS" in existing_ids:
            return True

        return False

    def _build_evidence(
        self,
        evidence_text: str,
        full_text: str,
        source: str,
        signal_id: str,
    ) -> Evidence:
        """Construct a reliable Evidence object. Locate offset if present, otherwise specify semantic context."""
        snippet = (evidence_text or "").strip()
        location = "semantic:context"
        context_window = snippet

        if snippet and full_text:
            idx = full_text.find(snippet)
            if idx != -1:
                start_char = idx
                end_char = idx + len(snippet)
                location = f"offset:{start_char}-{end_char}"
                ctx_start = max(0, start_char - 40)
                ctx_end = min(len(full_text), end_char + 40)
                context_window = full_text[ctx_start:ctx_end].replace("\n", " ").strip()

        return Evidence(
            value=snippet if snippet else "Contextual semantic finding",
            type="semantic_finding",
            source=source,
            location=location,
            context=context_window,
            normalized_value=snippet.lower() if snippet else "",
            metadata={
                "provider": self.provider.get_provider_name(),
                "semantic_signal_id": signal_id,
            },
        )
