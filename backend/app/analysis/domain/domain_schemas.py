"""Data schemas and contracts for ScamCheck External Domain Verification.

STATUS: FULLY IMPLEMENTED (Part 12)

Defines models for:
- DNSResolutionStatus & HTTPReachabilityStatus enums
- DomainRegistrationInfo (Registration metadata / RDAP / WHOIS abstraction)
- DomainTLSInfo (TLS / Certificate metadata)
- DomainVerificationReport (Consolidated result of verifying a single domain)
- DomainVerificationContext (Configuration and inputs for verification)
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.analysis.models import SignalSeverity


class DNSResolutionStatus(str, Enum):
    """Status of DNS resolution for a domain."""
    DOMAIN_RESOLVES = "domain_resolves"
    DOMAIN_DOES_NOT_RESOLVE = "domain_does_not_resolve"
    DNS_UNAVAILABLE = "dns_unavailable"
    DNS_TIMEOUT = "dns_timeout"
    BLOCKED_SSRF = "blocked_ssrf"


class HTTPReachabilityStatus(str, Enum):
    """Reachability status of a web endpoint."""
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    REDIRECT_LIMIT_EXCEEDED = "redirect_limit_exceeded"
    BLOCKED_SSRF = "blocked_ssrf"
    INVALID_SCHEME = "invalid_scheme"
    SKIPPED_OFFLINE = "skipped_offline"


class DomainRegistrationInfo(BaseModel):
    """Domain registration and age metadata abstraction."""
    domain: str = Field(..., description="Registered domain or apex domain name.")
    creation_date: Optional[str] = Field(None, description="ISO format domain creation / registration date.")
    age_days: Optional[int] = Field(None, description="Calculated domain age in days, if verifiable.")
    registrar: Optional[str] = Field(None, description="Name of registrar if publicly available.")
    expiration_date: Optional[str] = Field(None, description="ISO format domain expiration date.")
    status: str = Field(default="available", description="Metadata availability status ('available', 'unavailable', 'privacy_protected').")
    is_newly_registered: bool = Field(default=False, description="True if domain was registered recently (< 30 days).")


class DomainTLSInfo(BaseModel):
    """TLS and HTTPS certificate diagnostic metadata."""
    supports_https: bool = Field(default=False, description="Whether endpoint successfully negotiates HTTPS.")
    certificate_valid: Optional[bool] = Field(None, description="Whether certificate chain and hostname are valid.")
    issuer: Optional[str] = Field(None, description="Certificate authority / issuer.")
    days_until_expiry: Optional[int] = Field(None, description="Days until certificate expires.")
    error: Optional[str] = Field(None, description="TLS handshake or certificate error message.")


class DomainVerificationReport(BaseModel):
    """Comprehensive verification report for a single extracted domain/URL."""
    original_url: str = Field(..., description="Original input URL.")
    hostname: str = Field(..., description="Parsed domain hostname.")
    dns_status: DNSResolutionStatus = Field(default=DNSResolutionStatus.DNS_UNAVAILABLE)
    resolved_ips: List[str] = Field(default_factory=list, description="Public IP addresses resolved via DNS.")
    http_status: HTTPReachabilityStatus = Field(default=HTTPReachabilityStatus.SKIPPED_OFFLINE)
    status_code: Optional[int] = Field(None, description="Final HTTP status code.")
    final_url: Optional[str] = Field(None, description="Final landing URL after safe redirect traversal.")
    redirect_count: int = Field(default=0, description="Number of redirects followed.")
    is_https_downgrade: bool = Field(default=False, description="True if redirect traversed from HTTPS to insecure HTTP.")
    is_cross_domain_redirect: bool = Field(default=False, description="True if final destination belongs to an entirely different domain.")
    registration: Optional[DomainRegistrationInfo] = Field(None, description="Registration / WHOIS / RDAP metadata.")
    tls: Optional[DomainTLSInfo] = Field(None, description="TLS / HTTPS diagnostic info.")
    is_ssrf_blocked: bool = Field(default=False, description="True if target resolved to private or restricted network.")
    is_organization_consistent: Optional[bool] = Field(None, description="True if verified domain matches claimed employer.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic provider metadata.")
