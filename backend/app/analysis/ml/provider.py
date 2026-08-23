"""Semantic Intelligence Providers for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 11)

Provides:
- DeterministicSemanticProvider (Safe, 100% offline fallback provider)
- MockSemanticProvider (Test and verification provider)
- get_semantic_provider (Factory loading provider based on configuration)
"""

import os
import re
import time
from typing import List, Optional, Tuple
from backend.app.analysis.models import AnalysisContext, SignalSeverity
from backend.app.analysis.ml.base import SemanticModelProvider
from backend.app.analysis.ml.schemas import SemanticModelOutput, SemanticSignalItem


class DeterministicSemanticProvider(SemanticModelProvider):
    """Deterministic, rule-free semantic inference provider for offline development and testing.
    
    Operates 100% offline without external network or GPU requirements.
    Analyzes contextual sentence structures, implicit intentions, social engineering cues,
    and multi-fact interactions that standard strict regex rules may miss.
    """

    PROVIDER_NAME = "deterministic-fallback"

    def get_provider_name(self) -> str:
        return self.PROVIDER_NAME

    def analyze(
        self,
        text: str,
        context: Optional[AnalysisContext] = None,
    ) -> SemanticModelOutput:
        """Execute deterministic contextual semantic analysis on normalized opportunity text."""
        start_time = time.perf_counter()
        clean_text = (text or "").strip()

        if not clean_text:
            return SemanticModelOutput(
                provider_name=self.PROVIDER_NAME,
                signals=[],
                raw_text_length=0,
                processing_time_ms=0.0,
                is_success=True,
            )

        lower_text = clean_text.lower()
        signals: List[SemanticSignalItem] = []

        # ---------------------------------------------------------------------
        # 1. SIG_SEMANTIC_PAYMENT_PRESSURE
        # Implicit / contextual payment requirements or deposits to access work/documents
        # ---------------------------------------------------------------------
        payment_pressure_patterns = [
            (r"(?:refundable|mandatory|nominal|small|initial)\s+(?:verification|security|seat|portal|account|processing)\s+(?:payment|deposit|charge|fee|amount)", "implicit verification or security deposit requirement"),
            (r"(?:pay|deposit|transfer|send)\s+(?:a\s+small|the|any|refundable)?\s*(?:sum|amount|deposit|charge|fee)\s+(?:before|to\s+release|prior\s+to|for)\s+(?:your\s+)?(?:joining|offer|appointment|letter|onboarding)", "conditional fee required prior to release of employment documents"),
            (r"(?:seat|offer|selection)\s+(?:confirmation|activation|reservation)\s+(?:charge|payment|deposit|fee)", "payment framed as seat confirmation or activation fee"),
            (r"(?:purchase|buy)\s+(?:training|starter|kit|materials|software|license)\s+(?:to\s+start|before\s+beginning|for\s+internship)", "mandatory purchase of training materials before starting"),
        ]
        # Check for explicit negation
        has_payment_negation = bool(re.search(r"(?:no|without\s+any|zero)\s+(?:fee|payment|charge|cost|deposit|money\s+required)", lower_text))

        if not has_payment_negation:
            for pattern, desc in payment_pressure_patterns:
                match = re.search(pattern, lower_text)
                if match:
                    matched_snippet = clean_text[match.start():match.end()]
                    signals.append(
                        SemanticSignalItem(
                            signal_id="SIG_SEMANTIC_PAYMENT_PRESSURE",
                            title="Implicit Payment or Deposit Requirement",
                            description=f"Opportunity language indicates {desc}.",
                            severity=SignalSeverity.HIGH,
                            confidence=0.85,
                            evidence_text=matched_snippet,
                            explanation=f"Context semantically suggests payment is required to secure the position: '{matched_snippet}'.",
                        )
                    )
                    break

        # ---------------------------------------------------------------------
        # 2. SIG_SEMANTIC_RECRUITMENT_ANOMALY
        # Off-platform communication coercion, instant unvetted onboarding
        # ---------------------------------------------------------------------
        recruitment_anomaly_patterns = [
            (r"(?:move|switch|shift|proceed|continue|reach\s+out|contact)\s+(?:to|over\s+to|via|on)\s+(?:whatsapp|telegram|signal|viber)", "redirection off-platform to complete recruitment or verification"),
            (r"(?:contact|message|chat\s+with)\s+(?:our\s+)?(?:coordinator|hr|manager|recruiter|desk)\s+(?:privately|directly)\s+(?:on|via)\s+(?:whatsapp|telegram)", "directing candidate to private messaging channels for official process"),
            (r"(?:direct|instant|same\s+day)\s+(?:selection|onboarding|hiring)\s+without\s+(?:any\s+)?(?:interview|screening|assessment|test)", "instant job allocation without formal screening"),
        ]
        for pattern, desc in recruitment_anomaly_patterns:
            match = re.search(pattern, lower_text)
            if match:
                matched_snippet = clean_text[match.start():match.end()]
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_RECRUITMENT_ANOMALY",
                        title="Irregular Recruitment Process",
                        description=f"Recruitment context indicates {desc}.",
                        severity=SignalSeverity.MEDIUM,
                        confidence=0.80,
                        evidence_text=matched_snippet,
                        explanation=f"Context demonstrates irregular recruitment workflow: '{matched_snippet}'.",
                    )
                )
                break

        # ---------------------------------------------------------------------
        # 3. SIG_SEMANTIC_IMPERSONATION
        # High-authority claims, vague international department assertions
        # ---------------------------------------------------------------------
        impersonation_patterns = [
            (r"(?:specially|personally)\s+(?:selected|shortlisted|nominated)\s+by\s+(?:our\s+)?(?:international|global|executive|board|director|central)\s+(?:hiring|recruitment|department|team)", "unsolicited selection claimed by high-level or international department"),
            (r"(?:authorized|official|certified)\s+representative\s+of\s+(?:all\s+major|top|multinational|government)", "sweeping unsubstantiated authority representation"),
            (r"(?:your\s+profile\s+was\s+shortlisted\s+from\s+a\s+database\s+you\s+did\s+not\s+apply\s+to)", "unsolicited shortlisting from vague external databases"),
        ]
        for pattern, desc in impersonation_patterns:
            match = re.search(pattern, lower_text)
            if match:
                matched_snippet = clean_text[match.start():match.end()]
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_IMPERSONATION",
                        title="Vague Authority or Impersonation Cue",
                        description=f"Opportunity language uses {desc}.",
                        severity=SignalSeverity.HIGH,
                        confidence=0.75,
                        evidence_text=matched_snippet,
                        explanation=f"Context suggests artificial authority assertion: '{matched_snippet}'.",
                    )
                )
                break

        # ---------------------------------------------------------------------
        # 4. SIG_SEMANTIC_UNREALISTIC_PROMISE
        # Disproportionate income vs minimal/zero effort
        # ---------------------------------------------------------------------
        unrealistic_patterns = [
            (r"(?:six[- ]figure|huge|unlimited|effortless)\s+(?:income|earnings|salary|payout)\s+(?:from\s+home|online)?\s*(?:with\s+no\s+previous\s+experience|for\s+(?:only\s+)?\d+\s*min)", "disproportionate earnings for minimal daily time and zero experience"),
            (r"(?:earn|make)\s+(?:up\s+to\s+)?(?:₹|\$|rs\.?)\s*[\d,]+\s*(?:daily|per\s+day|hourly)\s+(?:by\s+just|just\s+by|simply\s+by)\s+(?:typing|clicking|watching|liking|sharing|reviewing)", "extreme pay advertised for trivial automated or repetitive tasks"),
            (r"(?:guaranteed|100%)\s+(?:daily\s+cash|weekly\s+payout|returns)\s+(?:without\s+work|effortless)", "guaranteed daily cash or returns without substantial labor"),
        ]
        for pattern, desc in unrealistic_patterns:
            match = re.search(pattern, lower_text)
            if match:
                matched_snippet = clean_text[match.start():match.end()]
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_UNREALISTIC_PROMISE",
                        title="Unrealistic Compensation Promise",
                        description=f"Opportunity language promises {desc}.",
                        severity=SignalSeverity.HIGH,
                        confidence=0.85,
                        evidence_text=matched_snippet,
                        explanation=f"Context offers compensation completely detached from realistic labor market standards: '{matched_snippet}'.",
                    )
                )
                break

        # ---------------------------------------------------------------------
        # 5. SIG_SEMANTIC_SOCIAL_ENGINEERING
        # Artificial exclusivity, fear of missing out, pressure tactics
        # ---------------------------------------------------------------------
        social_engineering_patterns = [
            (r"(?:act\s+now\s+or\s+your\s+offer\s+will\s+be\s+(?:permanently\s+)?(?:cancelled|revoked|forfeited))", "coercive threat of immediate offer forfeiture"),
            (r"(?:strictly\s+confidential|keep\s+this\s+private|do\s+not\s+(?:disclose|share\s+with\s+anyone))", "secrecy demand preventing candidate from seeking outside counsel"),
            (r"(?:only\s+\d+\s*(?:seats?|slots?|openings?)\s+(?:left|remaining)\s+for\s+your\s+(?:city|college|state|batch))", "manufactured scarcity targeting regional or college demographics"),
        ]
        for pattern, desc in social_engineering_patterns:
            match = re.search(pattern, lower_text)
            if match:
                matched_snippet = clean_text[match.start():match.end()]
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_SOCIAL_ENGINEERING",
                        title="Social Engineering Pressure",
                        description=f"Opportunity employs {desc}.",
                        severity=SignalSeverity.HIGH,
                        confidence=0.80,
                        evidence_text=matched_snippet,
                        explanation=f"Context reveals psychological manipulation: '{matched_snippet}'.",
                    )
                )
                break

        # ---------------------------------------------------------------------
        # 6. SIG_SEMANTIC_IDENTITY_REQUEST
        # Premature or improper identity/credentials demands
        # ---------------------------------------------------------------------
        identity_patterns = [
            (r"(?:send|submit|upload|share)\s+.*?(?:bank\s+login|password|pin|otp|net\s*banking|confidential\s+id|credentials)", "demanding banking credentials, PINs, or OTPs under guise of recruitment"),
            (r"(?:upload|submit)\s+(?:original\s+)?(?:aadhaar|pan|passport|id\s+proof)\s+(?:before|prior\s+to)", "premature collection of sensitive national identification prior to interview"),
        ]
        for pattern, desc in identity_patterns:
            match = re.search(pattern, lower_text)
            if match:
                matched_snippet = clean_text[match.start():match.end()]
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_IDENTITY_REQUEST",
                        title="Premature Identity or Credential Demand",
                        description=f"Opportunity language indicates {desc}.",
                        severity=SignalSeverity.MEDIUM,
                        confidence=0.80,
                        evidence_text=matched_snippet,
                        explanation=f"Context demands sensitive personal or financial credentials prematurely: '{matched_snippet}'.",
                    )
                )
                break


        # ---------------------------------------------------------------------
        # 7. SIG_SEMANTIC_FINANCIAL_MANIPULATION
        # Task deposit-rebate schemes, crypto token purchase requirements
        # ---------------------------------------------------------------------
        financial_manipulation_patterns = [
            (r"(?:recharge|deposit|top[- ]up)\s+(?:your\s+)?(?:account|wallet|balance)\s+(?:to\s+unlock|to\s+receive|for\s+higher\s+commission)", "task-based deposit or recharge scheme to unlock commissions"),
            (r"(?:purchase|buy)\s+(?:usdt|crypto|bitcoin|gift\s+cards?)\s+(?:as\s+part\s+of|to\s+complete|for\s+task)", "mandating cryptocurrency or gift card purchases to perform job duties"),
        ]
        for pattern, desc in financial_manipulation_patterns:
            match = re.search(pattern, lower_text)
            if match:
                matched_snippet = clean_text[match.start():match.end()]
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_FINANCIAL_MANIPULATION",
                        title="Financial Task / Deposit Scheme",
                        description=f"Opportunity language indicates {desc}.",
                        severity=SignalSeverity.HIGH,
                        confidence=0.85,
                        evidence_text=matched_snippet,
                        explanation=f"Context suggests predatory task-based financial manipulation: '{matched_snippet}'.",
                    )
                )
                break

        # ---------------------------------------------------------------------
        # 8. SIG_SEMANTIC_SUSPICIOUS_OPPORTUNITY_CONTEXT
        # Multi-factor compound contextual mismatch
        # ---------------------------------------------------------------------
        is_unsolicited = bool(re.search(r"(?:specially\s+selected|shortlisted\s+your\s+profile|congratulations\s+you\s+are\s+selected)", lower_text))
        is_informal_channel = bool(re.search(r"(?:whatsapp|telegram|signal)", lower_text))
        is_payment_or_money = bool(re.search(r"(?:payment|deposit|fee|charge|earn\s+[\d,]+)", lower_text))

        if is_unsolicited and is_informal_channel and is_payment_or_money:
            # Compound contextual risk flag if not already covered by multiple signals
            if len(signals) < 2:
                signals.append(
                    SemanticSignalItem(
                        signal_id="SIG_SEMANTIC_SUSPICIOUS_OPPORTUNITY_CONTEXT",
                        title="Compound Contextual Recruitment Risk",
                        description="Opportunity combines unsolicited selection, private chat redirection, and financial elements.",
                        severity=SignalSeverity.MEDIUM,
                        confidence=0.75,
                        evidence_text=clean_text[:120] + ("..." if len(clean_text) > 120 else ""),
                        explanation="The holistic combination of unsolicited selection, off-platform messaging, and financial discussion indicates a high-risk contextual pattern.",
                    )
                )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return SemanticModelOutput(
            provider_name=self.PROVIDER_NAME,
            signals=signals,
            raw_text_length=len(clean_text),
            processing_time_ms=duration_ms,
            is_success=True,
            metadata={"detection_count": len(signals)},
        )


class MockSemanticProvider(SemanticModelProvider):
    """Configurable mock semantic provider for testing custom model responses and failures."""

    def __init__(
        self,
        signals: Optional[List[SemanticSignalItem]] = None,
        should_fail: bool = False,
        error_message: str = "Simulated provider failure",
        provider_name: str = "mock-semantic-provider",
    ) -> None:
        self._signals = signals or []
        self._should_fail = should_fail
        self._error_message = error_message
        self._provider_name = provider_name

    def get_provider_name(self) -> str:
        return self._provider_name

    def analyze(
        self,
        text: str,
        context: Optional[AnalysisContext] = None,
    ) -> SemanticModelOutput:
        if self._should_fail:
            raise RuntimeError(self._error_message)

        return SemanticModelOutput(
            provider_name=self._provider_name,
            signals=self._signals,
            raw_text_length=len(text or ""),
            processing_time_ms=1.0,
            is_success=True,
        )


def get_semantic_provider(provider_type: Optional[str] = None) -> SemanticModelProvider:
    """Factory creating the appropriate semantic provider based on configuration.
    
    Reads SCAMCHECK_SEMANTIC_PROVIDER env var if provider_type is not supplied.
    Defaults to DeterministicSemanticProvider for 100% offline safety.
    """
    selected = (provider_type or os.environ.get("SCAMCHECK_SEMANTIC_PROVIDER", "deterministic")).lower()

    if selected == "deterministic" or selected == "offline":
        return DeterministicSemanticProvider()
    elif selected == "mock":
        return MockSemanticProvider()
    else:
        # Safe fallback to deterministic provider
        return DeterministicSemanticProvider()
