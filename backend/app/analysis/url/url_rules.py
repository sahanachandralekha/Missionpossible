"""URL Rules and Pattern Specifications for ScamCheck URL & Domain Intelligence.

STATUS: FULLY IMPLEMENTED (Part 10)

Defines:
- Standard URL risk signal specifications (titles, descriptions, severities, explanations)
- Known link shortener registry
- Generic job platform registry
- Corporate entity normalization tokens
- Suspicious redirect query parameters
"""

import re
from typing import Any, Dict, Set
from backend.app.analysis.models.enums import SignalSeverity


# -----------------------------------------------------------------------------
# 1. URL Risk Signal Specifications
# -----------------------------------------------------------------------------

URL_SIGNAL_SPECS: Dict[str, Dict[str, Any]] = {
    "SIG_INSECURE_URL": {
        "signal_type": "url_security",
        "title": "Insecure HTTP URL Scheme",
        "description": "The opportunity provides an unencrypted HTTP link rather than a secure HTTPS link.",
        "severity": SignalSeverity.LOW,
        "confidence": 0.90,
        "explanation": "Legitimate organizations and secure job portals standardly use HTTPS to protect user submissions. Unencrypted HTTP links should be verified with caution.",
    },
    "SIG_SHORTENED_URL": {
        "signal_type": "url_obfuscation",
        "title": "Shortened or Obfuscated URL",
        "description": "The opportunity uses a URL shortening service that conceals the true landing page and domain.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.95,
        "explanation": "URL shorteners hide the destination domain. Scammers frequently use link shorteners to disguise fake application portals or malicious landing pages.",
    },
    "SIG_IP_ADDRESS_URL": {
        "signal_type": "url_anomaly",
        "title": "Raw IP Address URL",
        "description": "The provided link points directly to a raw IPv4 numerical address rather than a registered domain name.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.95,
        "explanation": "Legitimate organizations host professional career pages on registered domain names, not raw numerical IP addresses.",
    },
    "SIG_URL_USERINFO": {
        "signal_type": "url_security",
        "title": "URL Contains Embedded User Credentials / Userinfo",
        "description": "The link contains embedded username or password authentication data in the URL structure.",
        "severity": SignalSeverity.HIGH,
        "confidence": 0.95,
        "explanation": "Embedded userinfo is a common phishing pattern used to disguise the actual destination host or spoof legitimate domain names.",
    },
    "SIG_UNUSUAL_URL_PORT": {
        "signal_type": "url_anomaly",
        "title": "Non-Standard URL Port",
        "description": "The link directs to a non-standard network port rather than standard web ports (80/443).",
        "severity": SignalSeverity.LOW,
        "confidence": 0.85,
        "explanation": "Public corporate application portals standardly use default web ports (80/443). Non-standard ports warrant additional verification.",
    },
    "SIG_EXCESSIVE_URL_LENGTH": {
        "signal_type": "url_anomaly",
        "title": "Excessively Long URL",
        "description": "The link contains an abnormally long URL structure.",
        "severity": SignalSeverity.LOW,
        "confidence": 0.80,
        "explanation": "Extremely long URLs with deeply nested parameters can be used to hide suspicious domains or redirect targets.",
    },
    "SIG_SUSPICIOUS_HOSTNAME": {
        "signal_type": "url_anomaly",
        "title": "Suspicious Hostname Structure",
        "description": "The hostname contains excessive subdomains, excessive hyphens, or unnatural character patterns.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.85,
        "explanation": "Domain names with excessive subdomains, repeated hyphens, or random character strings are frequently associated with disposable lookalike domains.",
    },
    "SIG_SUSPICIOUS_REDIRECT_PARAMETER": {
        "signal_type": "url_risk",
        "title": "Open Redirect Parameter Present in URL",
        "description": "The link contains redirect or destination parameters that may route visitors to an external third-party site.",
        "severity": SignalSeverity.LOW,
        "confidence": 0.85,
        "explanation": "URLs with redirect parameters (e.g. ?url=, ?redirect=) should be checked carefully to ensure they do not forward to unauthorized external portals.",
    },
    "SIG_DOMAIN_ORGANIZATION_MISMATCH": {
        "signal_type": "organization_mismatch",
        "title": "Claimed Organization / Domain Mismatch",
        "description": "The organization named in the opportunity does not closely correspond to the linked website domain.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.80,
        "explanation": "The organization name mentioned in the opportunity does not closely correspond to the supplied domain. Verify the domain through the organization's official website.",
    },
}


# -----------------------------------------------------------------------------
# 2. Known Link Shorteners Registry
# -----------------------------------------------------------------------------

KNOWN_SHORTENERS: Set[str] = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "is.gd",
    "ow.ly",
    "shorturl.at",
    "buff.ly",
    "cutt.ly",
    "goo.gl",
    "trib.al",
    "rebrand.ly",
    "tiny.cc",
    "s.id",
    "v.gd",
    "rb.gy",
    "clck.ru",
    "t.me",
    "wa.me",
}


# -----------------------------------------------------------------------------
# 3. Known Legitimate Job Platforms & Shared Form Hosts
# -----------------------------------------------------------------------------

GENERIC_JOB_PLATFORMS: Set[str] = {
    "linkedin.com",
    "internshala.com",
    "naukri.com",
    "indeed.com",
    "glassdoor.com",
    "unstop.com",
    "foundit.in",
    "monster.com",
    "forms.gle",
    "google.com",
    "docs.google.com",
    "forms.office.com",
    "typeform.com",
    "lever.co",
    "greenhouse.io",
    "workday.com",
    "smartrecruiters.com",
    "jobvite.com",
    "bamboohr.com",
    "ashbyhq.com",
    "github.com",
    "wellfound.com",
    "angellist.com",
}


# -----------------------------------------------------------------------------
# 4. Corporate Normalization Suffixes
# -----------------------------------------------------------------------------

CORP_SUFFIXES: Set[str] = {
    "pvt",
    "private",
    "ltd",
    "limited",
    "llc",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "technologies",
    "technology",
    "tech",
    "solutions",
    "services",
    "software",
    "systems",
    "group",
    "labs",
    "india",
    "global",
    "international",
    "enterprise",
    "enterprises",
    "ventures",
    "consulting",
}


# -----------------------------------------------------------------------------
# 5. Open Redirect & Destination Parameters
# -----------------------------------------------------------------------------

REDIRECT_PARAM_NAMES: Set[str] = {
    "redirect",
    "redirect_url",
    "redirect_to",
    "return",
    "return_url",
    "return_to",
    "next",
    "url",
    "target",
    "dest",
    "destination",
    "forward",
    "out",
    "link",
    "goto",
    "r",
    "u",
}


# -----------------------------------------------------------------------------
# 6. IPv4 Pattern
# -----------------------------------------------------------------------------

IPV4_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
