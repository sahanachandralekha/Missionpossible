"""Deterministic Entity Extractor for ScamCheck Analysis Layer.

STATUS: FULLY IMPLEMENTED (Part 6)

Architectural Role:
Identifies factual information (organizations, job roles, contacts, URLs,
monetary sums, payment requests, dates, and locations) from normalized text:
    AnalysisContext.opportunity.extracted_text -> ExtractedEntities + Evidence

CRITICAL ARCHITECTURAL BOUNDARY:
- Entity Extraction = "What factual information is present in the document?"
- Risk Detection   = "Why might that information indicate predatory risk?" (Future Phase)

EntityExtractor NEVER calculates risk scores, assigns severity, or classifies opportunities.
"""

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.analysis.models.analysis_context import AnalysisContext
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
from backend.app.analysis.models.evidence import Evidence


class EntityExtractor:
    """Deterministic, explainable extractor for structured factual entities and evidence markers."""

    # -------------------------------------------------------------------------
    # 1. Regex & Pattern Definitions
    # -------------------------------------------------------------------------

    # Common free/public webmail providers
    FREE_EMAIL_DOMAINS: Set[str] = {
        "gmail.com",
        "yahoo.com",
        "yahoo.co.in",
        "hotmail.com",
        "outlook.com",
        "rediffmail.com",
        "protonmail.com",
        "aol.com",
        "icloud.com",
        "zoho.com",
        "mail.com",
        "yandex.com",
    }

    # Known URL shortener domains
    URL_SHORTENERS: Set[str] = {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "is.gd",
        "buff.ly",
        "cutt.ly",
        "rb.gy",
        "shorturl.at",
    }

    # Standard email pattern
    EMAIL_REGEX = re.compile(
        r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"
    )

    # Standard URL pattern
    URL_REGEX = re.compile(
        r"\b((?:https?:\/\/|www\.)[^\s<>{}\[\]\"'`]+)"
    )

    # Monetary amounts (Symbols: ₹, $, €, £, ¥ and ISO/prefix codes: INR, Rs, USD, EUR, GBP, JPY)
    MONETARY_REGEX = re.compile(
        r"(?:"
        r"(?P<sym>[₹$€£¥])\s*(?P<amt1>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
        r"|"
        r"(?P<amt4>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?P<sym_post>[₹$€£¥])"
        r"|"
        r"(?P<code_pre>INR|Rs\.?|USD|EUR|GBP|JPY)\s*(?P<amt2>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
        r"|"
        r"(?P<amt3>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?P<code_post>INR|USD|EUR|GBP|JPY)"
        r")",
        re.IGNORECASE,
    )


    # Percentage expressions (e.g. 40%, 15% bonus, 100% guaranteed)
    PERCENTAGE_REGEX = re.compile(
        r"\b(?P<val>\d+(?:\.\d+)?)\s*%\s*(?P<ctx>[A-Za-z]+(?:\s+[A-Za-z]+){0,2})?",
        re.IGNORECASE,
    )

    # Phone numbers (national and international formats)
    PHONE_REGEX = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?"
        r"(?:\(?\d{2,4}\)?[-.\s]?)"
        r"\d{3,4}[-.\s]?\d{3,4}\b"
    )

    # Standard Date representations
    DATE_REGEXES = [
        # DD/MM/YYYY or DD-MM-YYYY or YYYY-MM-DD
        re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b"),
        re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b"),
        # Month DD, YYYY or DD Month YYYY (e.g. October 25, 2026 or 25 October 2026 or Nov 1, 2026)
        re.compile(
            r"\b(?:(?P<m1>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
            r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4}))\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:(\d{1,2})(?:st|nd|rd|th)?\s+(?P<m2>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
            r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+(\d{4}))\b",
            re.IGNORECASE,
        ),
    ]

    # Organization suffix indicators
    ORG_SUFFIX_REGEX = re.compile(
        r"\b([A-Z0-9][A-Za-z0-9&.\-']*(?:\s+[A-Z0-9][A-Za-z0-9&.\-']*){0,4}\s+"
        r"(?:Pvt\.?\s+Ltd\.?|Private\s+Limited|Ltd\.?|Limited|LLC|L\.L\.C\.|Inc\.?|"
        r"Incorporated|Corp\.?|Corporation|Technologies|Technology|Solutions|Systems|"
        r"Software|Company|Group|Labs|Services|Enterprises|Consulting|Infotech))\b"
    )

    # Job / Opportunity titles
    JOB_TITLE_PATTERNS = [
        r"\b(?:Software\s+Engineer|Software\s+Developer|Web\s+Developer|Frontend\s+Developer|"
        r"Front-End\s+Developer|Backend\s+Developer|Back-End\s+Developer|Full\s+Stack\s+Developer|"
        r"Full-Stack\s+Developer|Data\s+Analyst|Data\s+Scientist|UI/UX\s+Designer|UX\s+Designer|"
        r"UI\s+Designer|Graphic\s+Designer|Content\s+Writer|Copywriter|Marketing\s+Intern|"
        r"HR\s+Intern|Software\s+Intern|Engineering\s+Intern|Research\s+Intern|Graduate\s+Trainee|"
        r"Management\s+Trainee|Business\s+Development\s+Associate|Sales\s+Executive|"
        r"Digital\s+Marketing\s+Executive|DevOps\s+Engineer|Cloud\s+Architect|"
        r"Cybersecurity\s+Analyst|QA\s+Engineer|Quality\s+Analyst|Quality\s+Assurance|"
        r"Remote\s+Internship|Online\s+Internship|Part-Time\s+Job|Remote\s+Job|"
        r"Work\s+From\s+Home\s+Job|Work\s+From\s+Home\s+Internship|Internship|Intern)\b"
    ]
    JOB_TITLE_REGEX = re.compile("|".join(JOB_TITLE_PATTERNS), re.IGNORECASE)

    # Payment phrases & fee categories
    PAYMENT_PHRASES = [
        r"registration\s+fee",
        r"application\s+fee",
        r"processing\s+fee",
        r"security\s+deposit",
        r"training\s+fee",
        r"onboarding\s+fee",
        r"verification\s+fee",
        r"documentation\s+fee",
        r"refundable\s+deposit",
        r"laptop\s+deposit",
        r"material\s+fee",
        r"exam\s+fee",
        r"certification\s+fee",
        r"admission\s+fee",
        r"payment\s+required",
        r"pay\s+now",
        r"pay\s+immediately",
        r"transfer\s+money",
        r"deposit\s+amount",
        r"payment\s+to\s+confirm",
        r"fee\s+to\s+secure",
        r"fee\s+to\s+receive",
        r"send\s+deposit",
        r"upfront\s+fee",
        r"registration\s+charge",
        r"pay\s+(?:₹|\$|€|£|¥|INR|USD|EUR)\s*\d+",
    ]
    PAYMENT_REGEX = re.compile(r"\b(?:" + "|".join(PAYMENT_PHRASES) + r")\b", re.IGNORECASE)

    # UPI ID pattern
    UPI_REGEX = re.compile(
        r"\b([a-zA-Z0-9.\-_]{2,64}@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|ibl|axl|upi|postbank|apl))\b",
        re.IGNORECASE,
    )

    # Locations (Metros + Remote indicators)
    LOCATION_REGEX = re.compile(
        r"\b(?P<remote>Remote|Work\s+From\s+Home|Work-From-Home|WFH)\b|"
        r"\b(?P<city>Bangalore|Bengaluru|Mumbai|Delhi|New\s+Delhi|Hyderabad|Pune|Chennai|"
        r"Kolkata|Noida|Gurgaon|Gurugram|New\s+York|London|San\s+Francisco|Singapore|Toronto|Dubai)\b",
        re.IGNORECASE,
    )

    # Social media handle prefixes
    SOCIAL_REGEXES = {
        "telegram": re.compile(r"(?:telegram|tg|t\.me)\s*[:/]?\s*@?([A-Za-z0-9_]{4,32})\b", re.IGNORECASE),
        "whatsapp": re.compile(r"(?:whatsapp|wa\.me)\s*[:/]?\s*(\+?[0-9\s-]{10,16})\b", re.IGNORECASE),
        "instagram": re.compile(r"(?:instagram|ig|instagr\.am)\s*[:/]?\s*@?([A-Za-z0-9_.]{3,30})\b", re.IGNORECASE),
    }

    # -------------------------------------------------------------------------
    # 2. Main Extraction Orchestrator
    # -------------------------------------------------------------------------

    def extract(self, context: AnalysisContext) -> ExtractedEntities:
        """Extract structured entities from the normalized opportunity text in AnalysisContext.
        
        Args:
            context: AnalysisContext containing normalized OpportunityInput.
            
        Returns:
            Populated ExtractedEntities container.
        """
        entities, _ = self.extract_with_evidence(context)
        return entities

    def extract_with_evidence(
        self, context: AnalysisContext
    ) -> Tuple[ExtractedEntities, List[Evidence]]:
        """Extract entities and return both ExtractedEntities and a list of Evidence records.
        
        Args:
            context: AnalysisContext containing normalized OpportunityInput.
            
        Returns:
            Tuple of (ExtractedEntities, List[Evidence]).
        """
        text = ""
        source = "text"

        if context and context.opportunity:
            text = context.opportunity.extracted_text or ""
            source = str(context.opportunity.source_type.value if hasattr(context.opportunity.source_type, "value") else context.opportunity.source_type)

        return self.extract_from_text(text=text, source=source)

    def extract_from_text(
        self, text: str, source: str = "text"
    ) -> Tuple[ExtractedEntities, List[Evidence]]:
        """Direct extraction implementation operating on a normalized string."""
        evidence_list: List[Evidence] = []
        entities = ExtractedEntities()

        if not text or not text.strip():
            return entities, evidence_list

        # Run individual extraction subroutines
        entities.organizations = self._extract_organizations(text, source, evidence_list)
        entities.job_titles = self._extract_job_titles(text, source, evidence_list)
        entities.emails = self._extract_emails(text, source, evidence_list)
        entities.phone_numbers = self._extract_phones(text, source, evidence_list)
        entities.urls = self._extract_urls(text, source, evidence_list)
        entities.monetary_amounts = self._extract_monetary_amounts(text, source, evidence_list)
        entities.percentages = self._extract_percentages(text, source, evidence_list)
        entities.dates = self._extract_dates(text, source, evidence_list)
        entities.locations = self._extract_locations(text, source, evidence_list)
        entities.payment_details = self._extract_payment_details(text, source, evidence_list)
        entities.contact_info = self._aggregate_contact_info(
            text, entities.emails, entities.phone_numbers, entities.urls, source, evidence_list
        )

        return entities, evidence_list

    # -------------------------------------------------------------------------
    # 3. Individual Entity Extractors
    # -------------------------------------------------------------------------

    def _extract_organizations(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[OrganizationEntity]:
        """Extract company and business organization mentions."""
        orgs: List[OrganizationEntity] = []
        seen_names: Set[str] = set()

        for match in self.ORG_SUFFIX_REGEX.finditer(text):
            raw_name = match.group(1).strip()
            # Basic validation
            if len(raw_name) < 3 or raw_name.lower() in seen_names:
                continue

            seen_names.add(raw_name.lower())
            org = OrganizationEntity(
                name=raw_name,
                confidence=0.90,
            )
            orgs.append(org)

            # Build traceable evidence
            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="organization",
                    value=raw_name,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=raw_name,
                )
            )

        return orgs

    def _extract_job_titles(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[JobTitleEntity]:
        """Extract job positions, roles, and internship title mentions."""
        job_titles: List[JobTitleEntity] = []
        seen_titles: Set[str] = set()

        for match in self.JOB_TITLE_REGEX.finditer(text):
            raw_title = match.group(0).strip()
            if raw_title.lower() in seen_titles:
                continue

            seen_titles.add(raw_title.lower())
            job = JobTitleEntity(
                title=raw_title,
                confidence=0.95,
            )
            job_titles.append(job)

            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="job_title",
                    value=raw_title,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=raw_title.title(),
                )
            )

        return job_titles

    def _extract_emails(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[EmailEntity]:
        """Extract email addresses, provider type, and domain components."""
        emails: List[EmailEntity] = []
        seen_emails: Set[str] = set()

        for match in self.EMAIL_REGEX.finditer(text):
            full_email = match.group(0).strip()
            domain = match.group(2).strip().lower()

            if full_email.lower() in seen_emails:
                continue

            seen_emails.add(full_email.lower())
            is_free = domain in self.FREE_EMAIL_DOMAINS

            entity = EmailEntity(
                email=full_email,
                domain=domain,
                is_free_provider=is_free,
            )
            emails.append(entity)

            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="email",
                    value=full_email,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=full_email.lower(),
                    metadata={"domain": domain, "is_free_provider": is_free},
                )
            )

        return emails

    def _extract_phones(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[PhoneEntity]:
        """Extract telephone and mobile numbers."""
        phones: List[PhoneEntity] = []
        seen_phones: Set[str] = set()

        for match in self.PHONE_REGEX.finditer(text):
            raw_phone = match.group(0).strip()
            digits = re.sub(r"\D", "", raw_phone)

            # Filter out numbers that are too short (<7) or too long (>15)
            # or look like plain 4-digit years (e.g. 2026)
            if len(digits) < 7 or len(digits) > 15:
                continue

            # Check if this match is part of a date or monetary amount
            start, end = match.span()
            surrounding = text[max(0, start - 5):min(len(text), end + 5)]
            if re.search(r"[₹$€£¥/]", surrounding):
                continue

            if digits in seen_phones:
                continue

            seen_phones.add(digits)
            country_code = None
            if raw_phone.startswith("+"):
                parts = raw_phone.split()
                if len(parts) > 1:
                    country_code = parts[0]

            entity = PhoneEntity(
                number=raw_phone,
                country_code=country_code,
                normalized_number=f"+{digits}" if raw_phone.startswith("+") else digits,
            )
            phones.append(entity)

            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="phone_number",
                    value=raw_phone,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=entity.normalized_number,
                )
            )

        return phones

    def _extract_urls(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[UrlEntity]:
        """Extract web URLs and application hyperlinks."""
        urls: List[UrlEntity] = []
        seen_urls: Set[str] = set()

        for match in self.URL_REGEX.finditer(text):
            raw_url = match.group(1).strip()
            # Clean trailing punctuation attached from sentence boundaries
            clean_url = raw_url.rstrip(".,;!?)>]\'\"")
            if not clean_url or clean_url.lower() in seen_urls:
                continue

            seen_urls.add(clean_url.lower())

            # Parse URL components
            parse_target = clean_url if clean_url.startswith(("http://", "https://")) else f"http://{clean_url}"
            parsed = urllib.parse.urlparse(parse_target)
            domain = parsed.netloc.lower()
            path = parsed.path or None
            is_shortened = domain in self.URL_SHORTENERS

            entity = UrlEntity(
                url=clean_url,
                domain=domain,
                path=path,
                is_shortened=is_shortened,
            )
            urls.append(entity)

            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="url",
                    value=clean_url,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=parse_target.lower(),
                    metadata={
                        "domain": domain,
                        "path": path,
                        "query": parsed.query,
                        "fragment": parsed.fragment,
                        "is_shortened": is_shortened,
                    },
                )
            )

        return urls

    def _extract_monetary_amounts(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[MonetaryAmountEntity]:
        """Extract monetary sums, currencies, and figures."""
        amounts: List[MonetaryAmountEntity] = []
        seen_amounts: Set[str] = set()

        for match in self.MONETARY_REGEX.finditer(text):
            raw_match = match.group(0).strip()
            if raw_match.lower() in seen_amounts:
                continue
            seen_amounts.add(raw_match.lower())

            # Determine currency code & amount string
            currency = None
            amt_str = None

            if match.group("sym") and match.group("amt1"):
                sym = match.group("sym")
                currency = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(sym, sym)
                amt_str = match.group("amt1")
            elif match.group("sym_post") and match.group("amt4"):
                sym = match.group("sym_post")
                currency = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}.get(sym, sym)
                amt_str = match.group("amt4")
            elif match.group("code_pre") and match.group("amt2"):
                code = match.group("code_pre").upper().rstrip(".")
                currency = "INR" if code == "RS" else code
                amt_str = match.group("amt2")
            elif match.group("amt3") and match.group("code_post"):
                currency = match.group("code_post").upper()
                amt_str = match.group("amt3")


            numeric_val = None
            if amt_str:
                try:
                    numeric_val = float(amt_str.replace(",", ""))
                except ValueError:
                    pass

            # Classify context purpose
            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end, window=35)
            purpose = None
            ctx_lower = context_snippet.lower()
            if any(w in ctx_lower for w in ["fee", "deposit", "charge", "pay", "cost", "price", "transfer"]):
                purpose = "fee"
            elif any(w in ctx_lower for w in ["stipend", "salary", "per month", "/month", "/hr", "compensation", "earn"]):
                purpose = "compensation"

            entity = MonetaryAmountEntity(
                raw_amount=raw_match,
                currency=currency,
                numeric_value=numeric_val,
                purpose=purpose,
            )
            amounts.append(entity)

            evidence_list.append(
                Evidence(
                    type="monetary_amount",
                    value=raw_match,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=f"{numeric_val} {currency}" if numeric_val and currency else raw_match,
                    metadata={"numeric_value": numeric_val, "currency": currency, "purpose": purpose},
                )
            )

        return amounts

    def _extract_percentages(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[PercentageEntity]:
        """Extract percentage figures and contextual modifiers."""
        percentages: List[PercentageEntity] = []
        seen_pct: Set[str] = set()

        for match in self.PERCENTAGE_REGEX.finditer(text):
            raw_match = match.group(0).strip()
            if raw_match.lower() in seen_pct:
                continue
            seen_pct.add(raw_match.lower())

            val_str = match.group("val")
            ctx_str = match.group("ctx")
            numeric_val = None
            try:
                numeric_val = float(val_str)
            except ValueError:
                pass

            entity = PercentageEntity(
                raw_percentage=raw_match,
                numeric_value=numeric_val,
                context=ctx_str.strip() if ctx_str else None,
            )
            percentages.append(entity)

            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="percentage",
                    value=raw_match,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=f"{numeric_val}%" if numeric_val is not None else raw_match,
                )
            )

        return percentages

    def _extract_dates(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[DateEntity]:
        """Extract dates and deadlines."""
        dates: List[DateEntity] = []
        seen_dates: Set[str] = set()

        for date_regex in self.DATE_REGEXES:
            for match in date_regex.finditer(text):
                raw_date = match.group(0).strip()
                if raw_date.lower() in seen_dates:
                    continue
                seen_dates.add(raw_date.lower())

                start, end = match.span()
                context_snippet = self._get_context_snippet(text, start, end, window=30)
                ctx_lower = context_snippet.lower()

                date_type = None
                if any(w in ctx_lower for w in ["deadline", "last date", "apply by", "before", "till"]):
                    date_type = "deadline"
                elif any(w in ctx_lower for w in ["start", "joining", "commence", "commencement", "from"]):
                    date_type = "start_date"

                entity = DateEntity(
                    raw_date=raw_date,
                    date_type=date_type,
                )
                dates.append(entity)

                evidence_list.append(
                    Evidence(
                        type="date",
                        value=raw_date,
                        source=source,
                        location=f"offset:{start}-{end}",
                        context=context_snippet,
                        normalized_value=raw_date,
                        metadata={"date_type": date_type},
                    )
                )

        return dates

    def _extract_locations(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[LocationEntity]:
        """Extract city locations or remote work indicators."""
        locations: List[LocationEntity] = []
        seen_locs: Set[str] = set()

        for match in self.LOCATION_REGEX.finditer(text):
            raw_match = match.group(0).strip()
            if raw_match.lower() in seen_locs:
                continue
            seen_locs.add(raw_match.lower())

            is_remote = match.group("remote") is not None
            city = match.group("city")

            entity = LocationEntity(
                raw_location=raw_match,
                city=city,
                is_remote=is_remote or None,
            )
            locations.append(entity)

            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end)
            evidence_list.append(
                Evidence(
                    type="location",
                    value=raw_match,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=city or ("Remote" if is_remote else raw_match),
                )
            )

        return locations

    def _extract_payment_details(
        self, text: str, source: str, evidence_list: List[Evidence]
    ) -> List[PaymentDetailEntity]:
        """Extract explicit payment phrases, deposits, and UPI addresses."""
        payment_details: List[PaymentDetailEntity] = []
        seen_payments: Set[str] = set()

        # 1. Match payment action and fee phrases
        for match in self.PAYMENT_REGEX.finditer(text):
            raw_phrase = match.group(0).strip()
            if raw_phrase.lower() in seen_payments:
                continue
            seen_payments.add(raw_phrase.lower())

            start, end = match.span()
            context_snippet = self._get_context_snippet(text, start, end, window=40)

            # Check if there is an amount in the context snippet
            amount_match = self.MONETARY_REGEX.search(context_snippet)
            associated_amount = amount_match.group(0).strip() if amount_match else None

            # Standardize payment_type category
            phrase_lower = raw_phrase.lower()
            payment_type = "payment_request"
            if "registration" in phrase_lower:
                payment_type = "registration_fee"
            elif "security" in phrase_lower or "deposit" in phrase_lower:
                payment_type = "security_deposit"
            elif "training" in phrase_lower:
                payment_type = "training_fee"
            elif "application" in phrase_lower:
                payment_type = "application_fee"
            elif "processing" in phrase_lower or "verification" in phrase_lower:
                payment_type = "processing_fee"
            elif "onboarding" in phrase_lower or "documentation" in phrase_lower:
                payment_type = "onboarding_fee"

            entity = PaymentDetailEntity(
                payment_type=payment_type,
                amount=associated_amount,
            )
            payment_details.append(entity)

            evidence_list.append(
                Evidence(
                    type="payment_detail",
                    value=raw_phrase,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=payment_type,
                    metadata={"amount": associated_amount},
                )
            )

        # 2. Match UPI VPA addresses
        for upi_match in self.UPI_REGEX.finditer(text):
            upi_id = upi_match.group(1).strip()
            if upi_id.lower() in seen_payments:
                continue
            seen_payments.add(upi_id.lower())

            start, end = upi_match.span()
            context_snippet = self._get_context_snippet(text, start, end, window=30)

            entity = PaymentDetailEntity(
                payment_type="upi_handle",
                upi_id=upi_id,
                method="UPI",
            )
            payment_details.append(entity)

            evidence_list.append(
                Evidence(
                    type="payment_detail",
                    value=upi_id,
                    source=source,
                    location=f"offset:{start}-{end}",
                    context=context_snippet,
                    normalized_value=upi_id.lower(),
                    metadata={"method": "UPI", "upi_id": upi_id},
                )
            )

        return payment_details

    def _aggregate_contact_info(
        self,
        text: str,
        emails: List[EmailEntity],
        phones: List[PhoneEntity],
        urls: List[UrlEntity],
        source: str,
        evidence_list: List[Evidence],
    ) -> Optional[ContactInfoEntity]:
        """Aggregate contact vectors into a structured ContactInfoEntity."""
        email_strs = [e.email for e in emails]
        phone_strs = [p.number for p in phones]
        url_strs = [u.url for u in urls]
        social_handles: Dict[str, str] = {}

        for platform, regex in self.SOCIAL_REGEXES.items():
            for match in regex.finditer(text):
                handle = match.group(1).strip()
                social_handles[platform] = handle

                start, end = match.span()
                evidence_list.append(
                    Evidence(
                        type="social_handle",
                        value=handle,
                        source=source,
                        location=f"offset:{start}-{end}",
                        context=self._get_context_snippet(text, start, end),
                        normalized_value=handle,
                        metadata={"platform": platform},
                    )
                )

        if not email_strs and not phone_strs and not url_strs and not social_handles:
            return None

        primary_channel = "email" if email_strs else ("phone" if phone_strs else "web")
        if "telegram" in social_handles or "whatsapp" in social_handles:
            primary_channel = "messaging"

        return ContactInfoEntity(
            primary_channel=primary_channel,
            emails=email_strs,
            phone_numbers=phone_strs,
            urls=url_strs,
            social_handles=social_handles,
        )

    # -------------------------------------------------------------------------
    # 4. Helper Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _get_context_snippet(text: str, start: int, end: int, window: int = 25) -> str:
        """Extract a clean surrounding context window around a matched substring."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        snippet = text[ctx_start:ctx_end].replace("\n", " ").strip()
        return snippet
