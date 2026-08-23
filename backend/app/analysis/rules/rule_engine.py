"""Rule-Based Scam Signal Detection Engine for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 7)

Purpose:
Deterministically detects suspicious patterns (upfront fees, urgency coercion,
guaranteed placement, unrealistic compensation, informal channels, authority claims)
from normalized opportunity text and structured entity facts.

Architectural Boundary Invariants:
- Answers ONLY: "What suspicious patterns are present?"
- Does NOT calculate the 0-100 risk score (reserved for Part 8 RiskScoringEngine).
- Does NOT assign final RiskLevel.
- Does NOT classify scam vs not-scam.
- Operates 100% locally and deterministically with zero network/ML dependencies.
"""

from typing import Dict, List, Optional, Set
from backend.app.analysis.models.analysis_context import AnalysisContext
from backend.app.analysis.models.entities import ExtractedEntities
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.analysis.extraction.entity_extractor import EntityExtractor
from backend.app.analysis.rules.rule_catalog import (
    RULE_SPECS,
    UPFRONT_PAYMENT_REGEX,
    URGENCY_REGEX,
    GUARANTEED_OPPORTUNITY_REGEX,
    NO_INTERVIEW_REGEX,
    NO_EXPERIENCE_REGEX,
    UNREALISTIC_EARNINGS_REGEX,
    AUTHORITY_CLAIM_REGEX,
    INFORMAL_CONTACT_REGEX,
    UNSOLICITED_SELECTION_REGEX,
    DOCUMENT_CLAIM_REGEX,
)
from backend.app.analysis.rules.rule_helpers import (
    build_evidence,
    is_negated,
)


class RuleBasedSignalEngine:
    """Deterministic, explainable rule engine detecting scam signals from opportunity data."""

    def __init__(self):
        self._entity_extractor = EntityExtractor()

    def detect(
        self,
        context: AnalysisContext,
        entities: Optional[ExtractedEntities] = None,
        evidence: Optional[List[Evidence]] = None,
    ) -> List[RiskSignal]:
        """Detect risk signals from an AnalysisContext.
        
        Args:
            context: Analysis context containing OpportunityInput and optional facts.
            entities: Pre-extracted entities. If None, uses context.entities or extracts.
            evidence: Existing evidence pool to enrich.
            
        Returns:
            List of structured RiskSignal objects with traceable evidence.
        """
        text = context.opportunity.extracted_text if context.opportunity else ""
        if not text or not text.strip():
            return []

        source = "text"
        if context.opportunity and context.opportunity.source_type:
            source = context.opportunity.source_type.value

        # Resolve ExtractedEntities
        resolved_entities = entities or context.entities
        if resolved_entities is None:
            resolved_entities, _ = self._entity_extractor.extract_from_text(text, source=source)

        signals_map: Dict[str, RiskSignal] = {}

        # 1. Upfront Payment Detection
        self._detect_upfront_payment(text, resolved_entities, source, signals_map)

        # 2. Urgency & Pressure Language
        self._detect_urgency_pressure(text, resolved_entities, source, signals_map)

        # 3. Guaranteed Opportunity Claims
        self._detect_guaranteed_opportunity(text, resolved_entities, source, signals_map)

        # 4. No Interview / Instant Selection
        self._detect_no_interview(text, resolved_entities, source, signals_map)

        # 5. No Experience / Zero Qualification Claims
        self._detect_no_experience(text, resolved_entities, source, signals_map)

        # 6. Unrealistic or Effortless Earnings
        self._detect_unrealistic_earnings(text, resolved_entities, source, signals_map)

        # 7. Authority / Government Claims
        self._detect_authority_claims(text, resolved_entities, source, signals_map)

        # 8. Informal Contact / Redirection
        self._detect_informal_contact(text, resolved_entities, source, signals_map)

        # 9. Personal Payment Destination
        self._detect_personal_payment_destination(text, resolved_entities, source, signals_map)

        # 10. Unsolicited Selection / Recruitment Notice
        self._detect_unsolicited_selection(text, resolved_entities, source, signals_map)

        # 11. Document / Offer Claims
        self._detect_document_claims(text, resolved_entities, source, signals_map)

        # 12. Compound / Multi-Risk Combination Patterns
        self._detect_combination_patterns(signals_map, text, source)

        return list(signals_map.values())

    def detect_from_text(self, text: str, source: str = "text") -> List[RiskSignal]:
        """Convenience method to extract entities and detect signals directly from plain text."""
        if not text or not text.strip():
            return []

        entities, initial_evidence = self._entity_extractor.extract_from_text(text, source=source)
        signals_map: Dict[str, RiskSignal] = {}

        self._detect_upfront_payment(text, entities, source, signals_map)
        self._detect_urgency_pressure(text, entities, source, signals_map)
        self._detect_guaranteed_opportunity(text, entities, source, signals_map)
        self._detect_no_interview(text, entities, source, signals_map)
        self._detect_no_experience(text, entities, source, signals_map)
        self._detect_unrealistic_earnings(text, entities, source, signals_map)
        self._detect_authority_claims(text, entities, source, signals_map)
        self._detect_informal_contact(text, entities, source, signals_map)
        self._detect_personal_payment_destination(text, entities, source, signals_map)
        self._detect_unsolicited_selection(text, entities, source, signals_map)
        self._detect_document_claims(text, entities, source, signals_map)
        self._detect_combination_patterns(signals_map, text, source)

        return list(signals_map.values())

    # -------------------------------------------------------------------------
    # Internal Rule Detectors
    # -------------------------------------------------------------------------

    def _add_or_update_signal(
        self,
        signal_id: str,
        evidence_item: Evidence,
        signals_map: Dict[str, RiskSignal],
        source: str = "rule_engine",
        custom_metadata: Optional[dict] = None,
    ) -> None:
        """Helper to create or deduplicate risk signals by consolidating evidence."""
        if signal_id not in RULE_SPECS:
            return

        spec = RULE_SPECS[signal_id]

        if signal_id not in signals_map:
            signals_map[signal_id] = RiskSignal(
                signal_id=signal_id,
                signal_type=spec["signal_type"],
                title=spec["title"],
                description=spec["description"],
                severity=spec["severity"],
                confidence=spec["confidence"],
                evidence=[evidence_item],
                score_contribution=0.0,  # Explicitly neutral (risk scoring is separate)
                source=source,
                explanation=spec.get("explanation"),
                metadata=custom_metadata or {},
            )
        else:
            # Deduplicate evidence
            existing_signal = signals_map[signal_id]
            is_dup = any(
                e.value == evidence_item.value and e.location == evidence_item.location
                for e in existing_signal.evidence
            )
            if not is_dup:
                existing_signal.evidence.append(evidence_item)

    def _detect_upfront_payment(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect upfront payment demands, registration/security fees."""
        # 1. Regex pattern matches with negation check
        for match in UPFRONT_PAYMENT_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="upfront_fee_demand",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_UPFRONT_PAYMENT", ev, signals_map)

        # 2. Check structured PaymentDetailEntity items
        for p in entities.payment_details:
            if p.payment_type in [
                "registration_fee",
                "security_deposit",
                "training_fee",
                "application_fee",
                "payment_request",
            ]:
                # Find exact occurrence in text
                loc_str = p.amount or p.payment_type.replace("_", " ")
                pos = text.lower().find(loc_str.lower())
                if pos != -1:
                    start = pos
                    end = start + len(loc_str)
                    if is_negated(text, start, end):
                        continue

                    ev = build_evidence(
                        evidence_type="payment_detail_record",
                        value=f"{p.payment_type}: {p.amount or ''}".strip(),
                        source=source,
                        start=start,
                        end=end,
                        text=text,
                        metadata={"payment_type": p.payment_type, "amount": p.amount},
                    )
                    self._add_or_update_signal("SIG_UPFRONT_PAYMENT", ev, signals_map)


    def _detect_urgency_pressure(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect artificial urgency and high-pressure language."""
        for match in URGENCY_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="urgency_indicator",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_URGENCY_PRESSURE", ev, signals_map)

    def _detect_guaranteed_opportunity(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect unrealistic 100% guarantee promises for jobs, placements, or internships."""
        for match in GUARANTEED_OPPORTUNITY_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="guaranteed_claim",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_GUARANTEED_SELECTION", ev, signals_map)

    def _detect_no_interview(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect direct hiring or selection without screening/interview."""
        for match in NO_INTERVIEW_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="no_interview_claim",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_NO_INTERVIEW", ev, signals_map)

    def _detect_no_experience(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect zero experience / zero qualification claims."""
        for match in NO_EXPERIENCE_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="no_experience_claim",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_NO_EXPERIENCE", ev, signals_map)

    def _detect_unrealistic_earnings(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect too-good-to-be-true compensation or effortless income claims."""
        for match in UNREALISTIC_EARNINGS_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="unrealistic_earnings_claim",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_UNREALISTIC_EARNINGS", ev, signals_map)

    def _detect_authority_claims(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect claims of government approval or official affiliation."""
        for match in AUTHORITY_CLAIM_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="authority_endorsement_claim",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_AUTHORITY_CLAIM", ev, signals_map)

    def _detect_informal_contact(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect off-platform redirection to Telegram, WhatsApp, or Instagram for hiring."""
        for match in INFORMAL_CONTACT_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="informal_channel_redirection",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_INFORMAL_CONTACT_CHANNEL", ev, signals_map)

        # Check structured social handles if primary channel is informal
        if entities.contact_info and entities.contact_info.social_handles:
            for platform, handle in entities.contact_info.social_handles.items():
                if platform in ["telegram", "whatsapp", "instagram"] and (
                    "telegram" in text.lower() or "whatsapp" in text.lower()
                ):
                    pos = text.find(handle)
                    start = pos if pos != -1 else 0
                    end = start + len(handle) if pos != -1 else 0
                    ev = build_evidence(
                        evidence_type="social_contact_handle",
                        value=f"{platform}: {handle}",
                        source=source,
                        start=start,
                        end=end,
                        text=text,
                    )
                    self._add_or_update_signal("SIG_INFORMAL_CONTACT_CHANNEL", ev, signals_map)

    def _detect_personal_payment_destination(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect payment requests directed towards personal UPI IDs or private accounts."""
        for p in entities.payment_details:
            if p.upi_id:
                pos = text.find(p.upi_id)
                start = pos if pos != -1 else 0
                end = start + len(p.upi_id) if pos != -1 else 0
                ev = build_evidence(
                    evidence_type="personal_upi_destination",
                    value=p.upi_id,
                    source=source,
                    start=start,
                    end=end,
                    text=text,
                    metadata={"upi_id": p.upi_id, "amount": p.amount},
                )
                self._add_or_update_signal("SIG_PERSONAL_PAYMENT_DESTINATION", ev, signals_map)

    def _detect_unsolicited_selection(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect announcements of selection without application."""
        for match in UNSOLICITED_SELECTION_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="unsolicited_selection_notice",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_UNSOLICITED_SELECTION", ev, signals_map)

    def _detect_document_claims(
        self,
        text: str,
        entities: ExtractedEntities,
        source: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Detect references to attached or issued offer/appointment letters."""
        for match in DOCUMENT_CLAIM_REGEX.finditer(text):
            start, end = match.span()
            matched_str = match.group(0)

            if is_negated(text, start, end):
                continue

            ev = build_evidence(
                evidence_type="document_issuance_claim",
                value=matched_str,
                source=source,
                start=start,
                end=end,
                text=text,
            )
            self._add_or_update_signal("SIG_DOCUMENT_CLAIM", ev, signals_map)

    def _detect_combination_patterns(
        self,
        signals_map: Dict[str, RiskSignal],
        text: str,
        source: str,
    ) -> None:
        """Synthesize compound signals when multiple severe indicators co-occur.
        
        Note: Does NOT compute a risk score; merely emits an explainable compound signal.
        """
        has_fee = "SIG_UPFRONT_PAYMENT" in signals_map
        has_urgency = "SIG_URGENCY_PRESSURE" in signals_map
        has_guarantee = "SIG_GUARANTEED_SELECTION" in signals_map

        if has_fee and (has_urgency or has_guarantee):
            # Compound signal
            ev = build_evidence(
                evidence_type="compound_risk_pattern",
                value="Co-occurrence of upfront fee with urgency or guarantee",
                source=source,
                start=0,
                end=min(len(text), 80),
                text=text,
                metadata={
                    "co_occurring_signals": [
                        s for s in ["SIG_UPFRONT_PAYMENT", "SIG_URGENCY_PRESSURE", "SIG_GUARANTEED_SELECTION"]
                        if s in signals_map
                    ]
                },
            )
            self._add_or_update_signal("SIG_MULTIPLE_HIGH_RISK_PATTERNS", ev, signals_map)
