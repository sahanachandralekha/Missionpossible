"""External Domain Verification & Identity Intelligence Module for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 12)

Exports:
- DomainVerifier
- DomainVerificationProvider
- OfflineDomainVerificationProvider
- NetworkDomainVerificationProvider
- MockDomainVerificationProvider
- get_domain_verification_provider
- DomainVerificationReport
- DOMAIN_SIGNAL_SPECS
"""

from backend.app.analysis.domain.domain_rules import DOMAIN_SIGNAL_SPECS
from backend.app.analysis.domain.domain_schemas import (
    DNSResolutionStatus,
    DomainRegistrationInfo,
    DomainTLSInfo,
    DomainVerificationReport,
    HTTPReachabilityStatus,
)
from backend.app.analysis.domain.domain_verifier import DomainVerifier
from backend.app.analysis.domain.network_client import (
    DomainVerificationProvider,
    MockDomainVerificationProvider,
    NetworkDomainVerificationProvider,
    OfflineDomainVerificationProvider,
    get_domain_verification_provider,
)

__all__ = [
    "DNSResolutionStatus",
    "DOMAIN_SIGNAL_SPECS",
    "DomainRegistrationInfo",
    "DomainTLSInfo",
    "DomainVerificationProvider",
    "DomainVerificationReport",
    "DomainVerifier",
    "HTTPReachabilityStatus",
    "MockDomainVerificationProvider",
    "NetworkDomainVerificationProvider",
    "OfflineDomainVerificationProvider",
    "get_domain_verification_provider",
]
