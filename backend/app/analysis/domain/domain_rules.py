"""Domain Verification Rules, Signal Specifications, and Security Thresholds.

STATUS: FULLY IMPLEMENTED (Part 12)

Centralizes:
- SSRF network boundary rules (Private, Loopback, Link-Local, Multicast, Special IP ranges)
- Network timeout & resource bounds (Max redirects, max bytes, connect timeouts)
- Domain signal specifications and metadata
"""

import ipaddress
from typing import Any, Dict, List, Set
from backend.app.analysis.models import SignalSeverity

# -----------------------------------------------------------------------------
# 1. Network & Resource Safety Bounds
# -----------------------------------------------------------------------------

NETWORK_TIMEOUT_SECONDS: float = 3.0
MAX_REDIRECTS: int = 5
MAX_RESPONSE_BYTES: int = 65536  # 64 KB maximum inspection chunk
NEW_DOMAIN_DAYS_THRESHOLD: int = 30  # Flag domains registered less than 30 days ago
ALLOWED_SCHEMES: Set[str] = {"http", "https"}

# Blocked hostnames for SSRF defense
BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "169.254.169.254",  # AWS/GCP/Azure cloud metadata service
    "instance-data",
}

# Private and restricted IPv4 and IPv6 CIDR blocks
RESTRICTED_IP_NETWORKS: List[Any] = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),    # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("172.16.0.0/12"),   # Private
    ipaddress.ip_network("192.0.0.0/24"),    # IETF Protocol
    ipaddress.ip_network("192.0.2.0/24"),    # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),  # Private
    ipaddress.ip_network("198.18.0.0/15"),   # Network benchmark
    ipaddress.ip_network("198.51.100.0/24"), # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
    ipaddress.ip_network("240.0.0.0/4"),     # Reserved
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 ranges
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),         # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),        # Unique Local
    ipaddress.ip_network("fe80::/10"),       # Link-local
    ipaddress.ip_network("ff00::/8"),        # Multicast
]


def is_ip_restricted(ip_str: str) -> bool:
    """Check whether an IP address belongs to a private, loopback, link-local, or restricted network."""
    try:
        ip_obj = ipaddress.ip_address(ip_str.strip())
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified:
            return True
        for net in RESTRICTED_IP_NETWORKS:
            if ip_obj in net:
                return True
        return False
    except ValueError:
        return True  # If unparseable as IP, treat cautiously


def is_hostname_restricted(hostname: str) -> bool:
    """Check whether a hostname is explicitly blocked or points to localhost/internal domains."""
    if not hostname:
        return True
    host_clean = hostname.strip().lower().rstrip(".")
    if host_clean in BLOCKED_HOSTNAMES:
        return True
    if host_clean.endswith(".local") or host_clean.endswith(".internal") or host_clean.endswith(".localhost"):
        return True
    # If the hostname is literally an IP, check IP restriction
    try:
        ip_obj = ipaddress.ip_address(host_clean)
        return is_ip_restricted(str(ip_obj))
    except ValueError:
        pass
    return False


# -----------------------------------------------------------------------------
# 2. Domain Risk Signal Specifications
# -----------------------------------------------------------------------------

DOMAIN_SIGNAL_SPECS: Dict[str, Dict[str, Any]] = {
    "SIG_DOMAIN_UNRESOLVED": {
        "title": "Domain Name Fails DNS Resolution",
        "description": "The linked domain name cannot be resolved via DNS and has no valid public IP records.",
        "severity": SignalSeverity.LOW,
        "base_weight": 5.0,
        "default_confidence": 0.85,
        "category": "domain_verification",
    },
    "SIG_DOMAIN_REDIRECT_ANOMALY": {
        "title": "Suspicious Domain Redirection Behavior",
        "description": "The opportunity URL redirected across unrelated domains, downgraded from HTTPS to HTTP, or exceeded safe redirect limits.",
        "severity": SignalSeverity.MEDIUM,
        "base_weight": 10.0,
        "default_confidence": 0.90,
        "category": "domain_verification",
    },
    "SIG_DOMAIN_ORGANIZATION_INCONSISTENCY": {
        "title": "External Domain Identity Contradicts Claimed Organization",
        "description": "External domain verification confirms that the destination host does not belong to or represent the claimed hiring organization.",
        "severity": SignalSeverity.MEDIUM,
        "base_weight": 10.0,
        "default_confidence": 0.85,
        "category": "domain_verification",
    },
    "SIG_DOMAIN_TLS_ANOMALY": {
        "title": "TLS or Certificate Validation Anomaly",
        "description": "The domain endpoint fails TLS handshake, uses an invalid or expired certificate, or lacks HTTPS support for candidate intake.",
        "severity": SignalSeverity.LOW,
        "base_weight": 5.0,
        "default_confidence": 0.80,
        "category": "domain_verification",
    },
    "SIG_DOMAIN_REGISTRATION_ANOMALY": {
        "title": "Newly Registered Domain for Established Entity",
        "description": "The opportunity's domain was registered very recently (< 30 days) despite claiming to represent an established corporate brand.",
        "severity": SignalSeverity.MEDIUM,
        "base_weight": 10.0,
        "default_confidence": 0.85,
        "category": "domain_verification",
    },
    "SIG_DOMAIN_INFRASTRUCTURE_UNAVAILABLE": {
        "title": "Domain Infrastructure Temporarily Unavailable",
        "description": "The domain server timed out or returned a 5xx server error during reachability checks.",
        "severity": SignalSeverity.LOW,
        "base_weight": 5.0,
        "default_confidence": 0.70,
        "category": "domain_verification",
    },
}
