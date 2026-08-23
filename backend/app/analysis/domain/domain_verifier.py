"""External Domain Verification & Identity Intelligence Engine for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 12)

Coordinates:
- Verification of extracted opportunity URLs/domains against external identity records
- DNS resolution checks, reachability analysis, and redirect inspection
- TLS / HTTPS certificate validation
- Organization and domain consistency cross-checking
- Deduplication and evidence consolidation
- Strict failure isolation (provider outage != scam risk)
- score_contribution = 0.0 enforcement (RiskScoringEngine remains single scoring authority)
"""

from ast import Tuple
from typing import Any, Dict, List, Optional, Set
from backend.app.schemas.opportunity import SourceType
from backend.app.analysis.models import (
    AnalysisContext,
    Evidence,
    OrganizationEntity,
    RiskSignal,
    SignalSeverity,
    UrlEntity,
)
from backend.app.analysis.domain.domain_rules import DOMAIN_SIGNAL_SPECS
from backend.app.analysis.domain.domain_schemas import (
    DNSResolutionStatus,
    DomainVerificationReport,
    HTTPReachabilityStatus,
)
from backend.app.analysis.domain.network_client import (
    DomainVerificationProvider,
    get_domain_verification_provider,
)


class DomainVerifier:
    """External Domain Verification and Identity Intelligence layer."""

    def __init__(self, provider: Optional[DomainVerificationProvider] = None) -> None:
        self.provider = provider or get_domain_verification_provider()
        self.last_status: str = "initialized"
        self.last_error: Optional[str] = None
        self.last_checked_domains: List[str] = []

    def get_provider_name(self) -> str:
        """Return the active domain verification provider name."""
        return self.provider.get_provider_name()

    def verify(self, context: AnalysisContext) -> List[RiskSignal]:
        """Verify all URLs and organizations contained within an AnalysisContext.
        
        Args:
            context: Active AnalysisContext containing opportunity and extracted entities.
            
        Returns:
            List[RiskSignal]: Traceable domain verification risk signals.
        """
        if context is None or context.extracted_entities is None:
            return []

        urls = context.extracted_entities.urls or []
        orgs = context.extracted_entities.organizations or []
        source_type = (
            context.opportunity.source_type.value
            if context.opportunity and hasattr(context.opportunity.source_type, "value")
            else "text"
        )
        text = context.opportunity.extracted_text if context.opportunity else None

        return self.verify_urls(
            urls=urls,
            claimed_organizations=orgs,
            source=source_type,
            text=text,
        )

    def verify_urls(
        self,
        urls: List[UrlEntity],
        claimed_organizations: Optional[List[OrganizationEntity]] = None,
        source: str = "text",
        text: Optional[str] = None,
    ) -> List[RiskSignal]:
        """Verify a list of UrlEntity items against claimed organizations.
        
        Args:
            urls: Extracted UrlEntity objects.
            claimed_organizations: Optional list of OrganizationEntity objects.
            source: Source modality string ('text', 'image', 'pdf').
            text: Full text string for offset location.
            
        Returns:
            List[RiskSignal]: Traceable domain verification risk signals.
        """
        if not urls:
            self.last_status = "completed"
            self.last_checked_domains = []
            return []

        org_names = [org.name for org in claimed_organizations] if claimed_organizations else []
        signals_map: Dict[str, RiskSignal] = {}
        checked_hostnames: List[str] = []

        try:
            for url_entity in urls:
                url_str = (url_entity.url or "").strip()
                if not url_str:
                    continue

                report: DomainVerificationReport = self.provider.verify(
                    url=url_str,
                    claimed_organizations=org_names,
                )
                checked_hostnames.append(report.hostname)

                # Process report against domain signal specifications
                self._evaluate_report_signals(
                    report=report,
                    source=source,
                    text=text,
                    signals_map=signals_map,
                )

            self.last_status = "completed"
            self.last_error = None
            self.last_checked_domains = checked_hostnames

        except Exception as e:
            # Failure isolation: Provider error must not crash pipeline
            self.last_status = "failed"
            self.last_error = str(e)
            return []

        return list(signals_map.values())

    def _evaluate_report_signals(
        self,
        report: DomainVerificationReport,
        source: str,
        text: Optional[str],
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Evaluate a DomainVerificationReport and collect structured RiskSignal objects."""
        # 1. DNS Resolution Failure
        if report.dns_status == DNSResolutionStatus.DOMAIN_DOES_NOT_RESOLVE:
            self._add_signal(
                signal_id="SIG_DOMAIN_UNRESOLVED",
                report=report,
                evidence_value=f"Domain '{report.hostname}' fails DNS resolution",
                source=source,
                text=text,
                signals_map=signals_map,
                metadata={"dns_status": report.dns_status.value},
            )

        # 2. Redirect Anomaly (Cross-domain, HTTPS downgrade, or excessive redirects)
        if report.is_cross_domain_redirect or report.is_https_downgrade or report.redirect_count > 5:
            reason = "cross-domain redirect" if report.is_cross_domain_redirect else "HTTPS downgrade"
            self._add_signal(
                signal_id="SIG_DOMAIN_REDIRECT_ANOMALY",
                report=report,
                evidence_value=f"URL '{report.original_url}' exhibited {reason} to '{report.final_url}'",
                source=source,
                text=text,
                signals_map=signals_map,
                metadata={
                    "redirect_count": report.redirect_count,
                    "final_url": report.final_url,
                    "is_https_downgrade": report.is_https_downgrade,
                },
            )

        # 3. Organization Identity Inconsistency
        if report.is_organization_consistent is False:
            self._add_signal(
                signal_id="SIG_DOMAIN_ORGANIZATION_INCONSISTENCY",
                report=report,
                evidence_value=f"Domain '{report.hostname}' does not match claimed hiring organization identity",
                source=source,
                text=text,
                signals_map=signals_map,
                metadata={"hostname": report.hostname},
            )

        # 4. TLS Certificate Anomaly
        if report.tls and (report.tls.supports_https is False or report.tls.certificate_valid is False):
            tls_detail = report.tls.error or ("No HTTPS support" if not report.tls.supports_https else "Invalid TLS certificate")
            self._add_signal(
                signal_id="SIG_DOMAIN_TLS_ANOMALY",
                report=report,
                evidence_value=f"Domain '{report.hostname}' TLS anomaly: {tls_detail}",
                source=source,
                text=text,
                signals_map=signals_map,
                metadata={"tls_error": report.tls.error},
            )

        # 5. Newly Registered Domain Anomaly
        if report.registration and report.registration.is_newly_registered:
            age_desc = f"{report.registration.age_days} days old" if report.registration.age_days is not None else "newly registered"
            self._add_signal(
                signal_id="SIG_DOMAIN_REGISTRATION_ANOMALY",
                report=report,
                evidence_value=f"Domain '{report.hostname}' was registered very recently ({age_desc})",
                source=source,
                text=text,
                signals_map=signals_map,
                metadata={"age_days": report.registration.age_days},
            )

        # 6. Infrastructure Temporarily Unavailable (Non-critical informational)
        if report.http_status in [HTTPReachabilityStatus.TIMEOUT, HTTPReachabilityStatus.UNREACHABLE] and (report.status_code and report.status_code >= 500):
            self._add_signal(
                signal_id="SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE",
                report=report,
                evidence_value=f"Domain '{report.hostname}' server returned HTTP {report.status_code} or timed out",
                source=source,
                text=text,
                signals_map=signals_map,
                metadata={"status_code": report.status_code},
            )

    def _add_signal(
        self,
        signal_id: str,
        report: DomainVerificationReport,
        evidence_value: str,
        source: str,
        text: Optional[str],
        signals_map: Dict[str, RiskSignal],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create or consolidate a RiskSignal with traceable Evidence."""
        spec = DOMAIN_SIGNAL_SPECS.get(signal_id)
        if not spec:
            return

        evidence_loc, evidence_ctx = self._find_location_and_context(report.original_url, text)
        evidence_item = Evidence(
            value=evidence_value,
            type="domain_verification",
            source=source,
            location=evidence_loc,
            context=evidence_ctx,
            normalized_value=report.hostname.lower(),
            metadata={
                "hostname": report.hostname,
                "original_url": report.original_url,
                "provider": self.provider.get_provider_name(),
                **(metadata or {}),
            },
        )

        if signal_id in signals_map:
            # Deduplicate signal: consolidate evidence
            signals_map[signal_id].evidence.append(evidence_item)
        else:
            signals_map[signal_id] = RiskSignal(
                signal_id=signal_id,
                signal_type=spec.get("category", "domain_verification"),
                title=spec["title"],
                description=spec["description"],
                severity=spec["severity"],
                confidence=spec.get("default_confidence", 0.85),
                evidence=[evidence_item],
                score_contribution=0.0,  # Single authority: RiskScoringEngine
                metadata={
                    "provider": self.provider.get_provider_name(),
                    "analysis_type": "domain_verification",
                },
            )

    def _find_location_and_context(self, url: str, text: Optional[str]) -> Tuple[str, Optional[str]]:
        """Locate character offset range and surrounding context snippet if text is available."""
        if not text or not url:
            return "domain:external", None

        idx = text.find(url)
        if idx == -1:
            return "domain:external", None

        start_char = idx
        end_char = idx + len(url)
        ctx_start = max(0, start_char - 30)
        ctx_end = min(len(text), end_char + 30)
        context_str = text[ctx_start:ctx_end].replace("\n", " ").strip()
        return f"offset:{start_char}-{end_char}", context_str
