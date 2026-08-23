"""URL and Domain Structure Intelligence Analyzer for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 10)

Purpose:
Analyzes the structural characteristics of URLs extracted from opportunities.
Detects insecure schemes, link shorteners, IP address endpoints, userinfo auth vectors,
unusual ports, excessive lengths, suspicious hostname structures, open redirect parameters,
and claimed organization/domain mismatches.

Architectural Boundaries:
- Answers ONLY: "What structural characteristics and anomalies do the URLs contain?"
- Does NOT perform DNS queries, WHOIS/RDAP queries, or network requests.
- Does NOT calculate the final 0-100 risk score (reserved for RiskScoringEngine).
- Operates 100% locally, deterministically, and passively on string representations.
"""

import re
import urllib.parse
from typing import Dict, List, Optional, Set
from backend.app.analysis.models.analysis_context import AnalysisContext
from backend.app.analysis.models.entities import ExtractedEntities, OrganizationEntity, UrlEntity
from backend.app.analysis.models.evidence import Evidence
from backend.app.analysis.models.risk_signal import RiskSignal
from backend.app.analysis.url.url_rules import (
    CORP_SUFFIXES,
    GENERIC_JOB_PLATFORMS,
    IPV4_REGEX,
    KNOWN_SHORTENERS,
    REDIRECT_PARAM_NAMES,
    URL_SIGNAL_SPECS,
)


class UrlAnalyzer:
    """Deterministic, explainable URL structure and domain characteristics analyzer."""

    def analyze(self, context: AnalysisContext) -> List[RiskSignal]:
        """Analyze all extracted URLs within an AnalysisContext.
        
        Args:
            context: AnalysisContext containing opportunity text, source, and ExtractedEntities.
            
        Returns:
            List[RiskSignal]: Deduplicated list of detected URL structural risk signals.
        """
        if not context or not context.opportunity:
            return []

        source = "text"
        if context.opportunity.source_type:
            source = context.opportunity.source_type.value

        text = context.opportunity.extracted_text or ""
        urls: List[UrlEntity] = []
        orgs: List[OrganizationEntity] = []

        if context.extracted_entities:
            urls = context.extracted_entities.urls
            orgs = context.extracted_entities.organizations

        return self.analyze_urls(urls=urls, source=source, organizations=orgs, text=text)

    def analyze_urls(
        self,
        urls: List[UrlEntity],
        source: str = "text",
        organizations: Optional[List[OrganizationEntity]] = None,
        text: Optional[str] = None,
    ) -> List[RiskSignal]:
        """Analyze a list of UrlEntity instances.
        
        Args:
            urls: List of structured UrlEntity objects.
            source: Source modality ('text', 'image', 'pdf').
            organizations: Extracted organization mentions for domain consistency comparison.
            text: Full extracted opportunity text for evidence context and location extraction.
            
        Returns:
            List[RiskSignal]: List of detected URL risk signals with traceable evidence.
        """
        if not urls:
            return []

        signals_map: Dict[str, RiskSignal] = {}

        for url_entity in urls:
            url_str = (url_entity.url or "").strip()
            if not url_str:
                continue

            self._analyze_single_url(
                url_str=url_str,
                url_entity=url_entity,
                source=source,
                organizations=organizations or [],
                text=text or "",
                signals_map=signals_map,
            )

        return list(signals_map.values())

    def _analyze_single_url(
        self,
        url_str: str,
        url_entity: UrlEntity,
        source: str,
        organizations: List[OrganizationEntity],
        text: str,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Parse and evaluate structural risk rules for a single URL string."""
        try:
            # Prepend dummy scheme if missing to ensure netloc/host are parsed properly
            parse_target = url_str
            has_scheme = "://" in url_str
            if not has_scheme:
                parse_target = "http://" + url_str

            parsed = urllib.parse.urlsplit(parse_target)
            scheme = parsed.scheme.lower() if has_scheme else ""
            raw_netloc = parsed.netloc or ""
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
            path = parsed.path or ""
            query = parsed.query or ""
            username = parsed.username
            password = parsed.password
        except Exception:
            return

        has_userinfo = bool(username or password or ("@" in raw_netloc))
        clean_hostname = hostname.replace("www.", "")
        url_len = len(url_str)
        evidence_loc, evidence_ctx = self._find_location_and_context(url_str, text)


        # ---------------------------------------------------------------------
        # Rule A: Insecure HTTP Scheme
        # ---------------------------------------------------------------------
        if scheme == "http":
            ev = self._create_evidence(
                evidence_type="insecure_http_url",
                value=url_str,
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"scheme": "http", "hostname": hostname},
            )
            self._add_or_update_signal("SIG_INSECURE_URL", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule B: URL Shorteners
        # ---------------------------------------------------------------------
        if clean_hostname in KNOWN_SHORTENERS or any(clean_hostname.endswith("." + s) for s in KNOWN_SHORTENERS):
            ev = self._create_evidence(
                evidence_type="shortened_url",
                value=url_str,
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"shortener_host": clean_hostname},
            )
            self._add_or_update_signal("SIG_SHORTENED_URL", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule C: Raw IP Address Hostname
        # ---------------------------------------------------------------------
        if IPV4_REGEX.match(hostname):
            ev = self._create_evidence(
                evidence_type="ip_address_url",
                value=url_str,
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"ip_address": hostname},
            )
            self._add_or_update_signal("SIG_IP_ADDRESS_URL", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule D: Suspicious Userinfo / Embedded Credentials
        # ---------------------------------------------------------------------
        if has_userinfo:
            ev = self._create_evidence(
                evidence_type="url_userinfo",
                value=url_str,
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"userinfo_detected": True},
            )
            self._add_or_update_signal("SIG_URL_USERINFO", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule E: Unusual / Non-Standard Network Port
        # ---------------------------------------------------------------------
        if port is not None and port not in (80, 443):
            ev = self._create_evidence(
                evidence_type="unusual_url_port",
                value=url_str,
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"port": port},
            )
            self._add_or_update_signal("SIG_UNUSUAL_URL_PORT", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule F: Excessively Long URL
        # ---------------------------------------------------------------------
        if url_len > 160:
            ev = self._create_evidence(
                evidence_type="excessive_url_length",
                value=url_str,
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"length": url_len},
            )
            self._add_or_update_signal("SIG_EXCESSIVE_URL_LENGTH", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule G: Suspicious Hostname Structure
        # ---------------------------------------------------------------------
        if hostname and not IPV4_REGEX.match(hostname):
            subdomain_count = hostname.count(".")
            hyphen_count = hostname.count("-")
            digit_count = sum(c.isdigit() for c in hostname)
            digit_ratio = digit_count / len(hostname) if len(hostname) > 0 else 0.0

            is_suspicious_host = (
                subdomain_count >= 4
                or hyphen_count >= 3
                or (len(hostname) > 40 and hyphen_count >= 2)
                or (digit_ratio > 0.35 and len(hostname) > 10)
            )

            if is_suspicious_host:
                ev = self._create_evidence(
                    evidence_type="suspicious_hostname",
                    value=hostname,
                    source=source,
                    location=evidence_loc,
                    context=evidence_ctx,
                    metadata={
                        "hostname": hostname,
                        "subdomains": subdomain_count,
                        "hyphens": hyphen_count,
                        "digit_ratio": round(digit_ratio, 2),
                    },
                )
                self._add_or_update_signal("SIG_SUSPICIOUS_HOSTNAME", ev, signals_map)

        # ---------------------------------------------------------------------
        # Rule H: Open Redirect / Suspicious Target Query Parameter
        # ---------------------------------------------------------------------
        if query:
            query_params = urllib.parse.parse_qs(query, keep_blank_values=True)
            for param_name, param_values in query_params.items():
                if param_name.lower() in REDIRECT_PARAM_NAMES:
                    if any(
                        v.startswith(("http://", "https://", "//"))
                        or "." in v
                        for v in param_values if v
                    ):
                        ev = self._create_evidence(
                            evidence_type="redirect_parameter",
                            value=url_str,
                            source=source,
                            location=evidence_loc,
                            context=evidence_ctx,
                            metadata={"parameter": param_name, "destination": param_values[0] if param_values else ""},
                        )
                        self._add_or_update_signal("SIG_SUSPICIOUS_REDIRECT_PARAMETER", ev, signals_map)
                        break

        # ---------------------------------------------------------------------
        # Rule I: Claimed Organization vs Domain Mismatch
        # ---------------------------------------------------------------------
        self._check_organization_domain_consistency(
            hostname=clean_hostname,
            url_str=url_str,
            source=source,
            evidence_loc=evidence_loc,
            evidence_ctx=evidence_ctx,
            organizations=organizations,
            signals_map=signals_map,
        )

    def _check_organization_domain_consistency(
        self,
        hostname: str,
        url_str: str,
        source: str,
        evidence_loc: str,
        evidence_ctx: Optional[str],
        organizations: List[OrganizationEntity],
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Compare claimed organization names against the URL domain."""
        if not organizations or not hostname:
            return

        # Do not flag generic job boards, form hosting portals, or shorteners
        if (
            hostname in GENERIC_JOB_PLATFORMS
            or any(hostname.endswith("." + p) for p in GENERIC_JOB_PLATFORMS)
            or hostname in KNOWN_SHORTENERS
            or IPV4_REGEX.match(hostname)
        ):
            return

        # Collect meaningful org keywords
        org_matched = False
        has_meaningful_org = False

        for org in organizations:
            org_name = org.name.lower()
            tokens = self._extract_org_tokens(org_name)
            if not tokens:
                continue

            has_meaningful_org = True

            # If any token is in the hostname (e.g. 'apex' in 'apextechnologies.com'), it matches
            if any(t in hostname for t in tokens):
                org_matched = True
                break

        if has_meaningful_org and not org_matched:
            claimed_names = ", ".join(o.name for o in organizations[:2])
            ev = self._create_evidence(
                evidence_type="org_domain_mismatch",
                value=f"Claimed: '{claimed_names}' vs Domain: '{hostname}'",
                source=source,
                location=evidence_loc,
                context=evidence_ctx,
                metadata={"claimed_organizations": claimed_names, "url_domain": hostname},
            )
            self._add_or_update_signal("SIG_DOMAIN_ORGANIZATION_MISMATCH", ev, signals_map)

    @staticmethod
    def _extract_org_tokens(org_name: str) -> Set[str]:
        """Extract root keywords from an organization name by stripping corporate suffixes."""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", org_name).lower()
        raw_tokens = cleaned.split()
        return {
            t for t in raw_tokens
            if len(t) >= 3 and t not in CORP_SUFFIXES
        }

    @staticmethod
    def _find_location_and_context(url_str: str, text: str) -> tuple[str, Optional[str]]:
        """Find character offset and context snippet in text if available."""
        if not text:
            return "url", None

        pos = text.find(url_str)
        if pos == -1:
            return "url", None

        start = pos
        end = start + len(url_str)
        ctx_start = max(0, start - 30)
        ctx_end = min(len(text), end + 30)
        snippet = text[ctx_start:ctx_end].replace("\n", " ").strip()
        return f"offset:{start}-{end}", snippet

    @staticmethod
    def _create_evidence(
        evidence_type: str,
        value: str,
        source: str,
        location: str,
        context: Optional[str],
        metadata: dict,
    ) -> Evidence:
        """Helper to create standardized Evidence instances for URL signals."""
        return Evidence(
            type=evidence_type,
            value=value,
            source=source,
            location=location,
            context=context,
            normalized_value=value,
            metadata=metadata,
        )

    @staticmethod
    def _add_or_update_signal(
        signal_id: str,
        evidence_item: Evidence,
        signals_map: Dict[str, RiskSignal],
    ) -> None:
        """Add or consolidate URL signals to avoid duplicate signal categories."""
        if signal_id not in URL_SIGNAL_SPECS:
            return

        spec = URL_SIGNAL_SPECS[signal_id]

        if signal_id not in signals_map:
            signals_map[signal_id] = RiskSignal(
                signal_id=signal_id,
                signal_type=spec["signal_type"],
                title=spec["title"],
                description=spec["description"],
                severity=spec["severity"],
                confidence=spec["confidence"],
                evidence=[evidence_item],
                score_contribution=0.0,  # Explicitly neutral; RiskScoringEngine owns scoring
                source="url_analyzer",
                explanation=spec.get("explanation"),
                metadata={},
            )
        else:
            existing_signal = signals_map[signal_id]
            is_dup = any(
                e.value == evidence_item.value and e.location == evidence_item.location
                for e in existing_signal.evidence
            )
            if not is_dup:
                existing_signal.evidence.append(evidence_item)
