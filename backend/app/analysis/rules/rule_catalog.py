"""Rule Catalog and Regular Expression Definitions for ScamCheck Signal Engine.

STATUS: FULLY IMPLEMENTED (Part 7)

Definitions:
- Compiled deterministic pattern regexes
- Standard signal identifiers, categories, titles, default severities, and student guidance
"""

import re
from typing import Dict, Pattern
from backend.app.analysis.models.enums import SignalSeverity


# -----------------------------------------------------------------------------
# 1. Compiled Pattern Definitions
# -----------------------------------------------------------------------------

UPFRONT_PAYMENT_REGEX = re.compile(
    r"\b(?:"
    r"registration\s+fees?|"
    r"application\s+fees?|"
    r"processing\s+fees?|"
    r"security\s+deposits?|"
    r"security\s+money|"
    r"caution\s+money|"
    r"training\s+fees?|"
    r"joining\s+fees?|"
    r"onboarding\s+fees?|"
    r"verification\s+fees?|"
    r"documentation\s+fees?|"
    r"refundable\s+deposits?|"
    r"laptop\s+deposits?|"
    r"material\s+fees?|"
    r"exam\s+fees?|"
    r"certification\s+fees?|"
    r"admission\s+fees?|"
    r"pay\s+(?:₹|\$|€|£|¥|INR|USD|EUR)\s*\d+(?:,\d{3})*|"
    r"deposit\s+(?:₹|\$|€|£|¥|INR|USD|EUR)\s*\d+(?:,\d{3})*|"
    r"transfer\s+(?:₹|\$|€|£|¥|INR|USD|EUR)\s*\d+(?:,\d{3})*|"
    r"send\s+(?:₹|\$|€|£|¥|INR|USD|EUR)\s*\d+(?:,\d{3})*|"
    r"send\s+payment|"
    r"payment\s+required|"
    r"deposit\s+required|"
    r"pay\s+before\s+joining|"
    r"pay\s+to\s+confirm|"
    r"pay\s+to\s+secure(?:\s+your\s+position)?|"
    r"pay\s+to\s+receive(?:\s+offer)?|"
    r"upfront\s+fee"
    r")\b",
    re.IGNORECASE,
)


URGENCY_REGEX = re.compile(
    r"\b(?:"
    r"act\s+now|"
    r"apply\s+immediately|"
    r"urgent(?:ly)?|"
    r"immediately|"
    r"right\s+now|"
    r"right\s+away|"
    r"limited\s+slots?|"
    r"limited\s+seats?|"
    r"today\s+only|"
    r"respond\s+immediately|"
    r"within\s+\d+\s+hours?|"
    r"last\s+chance|"
    r"don't\s+miss\s+this\s+opportunity|"
    r"offer\s+expires(?:\s+soon|\s+today|\s+immediately)?|"
    r"pay\s+immediately|"
    r"confirm\s+immediately|"
    r"do\s+it\s+now|"
    r"immediate\s+joining\s+required|"
    r"seats\s+filling\s+fast|"
    r"hurry\s+up"
    r")\b",
    re.IGNORECASE,
)

GUARANTEED_OPPORTUNITY_REGEX = re.compile(
    r"\b(?:"
    r"guaranteed\s+(?:remote\s+|online\s+|virtual\s+|paid\s+)?job|"
    r"100%\s+job\s+guarantee|"
    r"guaranteed\s+(?:remote\s+|online\s+|virtual\s+|paid\s+)?placement|"
    r"guaranteed\s+(?:remote\s+|online\s+|virtual\s+|paid\s+)?selection|"
    r"guaranteed\s+(?:remote\s+|online\s+|virtual\s+|paid\s+)?internship|"
    r"100%\s+placement|"
    r"job\s+guaranteed|"
    r"selection\s+guaranteed|"
    r"assured\s+(?:remote\s+|online\s+|virtual\s+|paid\s+)?job|"
    r"confirmed\s+job\s+without\s+interview|"
    r"100%\s+selection\s+guaranteed|"
    r"guaranteed\s+offer"
    r")\b",
    re.IGNORECASE,
)


NO_INTERVIEW_REGEX = re.compile(
    r"\b(?:"
    r"no\s+interview\s+required|"
    r"no\s+interview|"
    r"selected\s+without\s+interview|"
    r"direct\s+selection|"
    r"selection\s+without\s+interview|"
    r"instant\s+selection|"
    r"no\s+test\s+required|"
    r"direct\s+hiring"
    r")\b",
    re.IGNORECASE,
)

NO_EXPERIENCE_REGEX = re.compile(
    r"\b(?:"
    r"no\s+experience\s+required|"
    r"no\s+prior\s+experience|"
    r"anyone\s+can\s+get\s+selected|"
    r"no\s+skills\s+needed|"
    r"zero\s+experience\s+needed"
    r")\b",
    re.IGNORECASE,
)

UNREALISTIC_EARNINGS_REGEX = re.compile(
    r"\b(?:"
    r"earn\s+(?:₹|\$|€|£|INR|USD)\s*(?:1\s*lakh|\d{5,})\s+(?:per\s+week|daily|every\s+week|per\s+day)|"
    r"earn\s+huge\s+money(?:\s+instantly)?|"
    r"make\s+huge\s+money(?:\s+instantly)?|"
    r"guaranteed\s+(?:₹|\$|€|£|INR|USD)\s*\d+\s+daily|"
    r"effortless\s+income|"
    r"easy\s+money\s+from\s+home|"
    r"earn\s+\d+.*(?:1\s*hour|few\s+minutes)\s+of\s+work"
    r")\b",
    re.IGNORECASE,
)

AUTHORITY_CLAIM_REGEX = re.compile(
    r"\b(?:"
    r"official\s+government\s+internship|"
    r"government\s+approved\s+job|"
    r"official\s+HR|"
    r"verified\s+by\s+government|"
    r"Ministry\s+approved|"
    r"official\s+recruitment\s+partner|"
    r"certified\s+government\s+project|"
    r"Govt\.?\s+of\s+India\s+certified"
    r")\b",
    re.IGNORECASE,
)

INFORMAL_CONTACT_REGEX = re.compile(
    r"\b(?:"
    r"contact\s+(?:me|us|recruiter|HR)?\s*(?:on|via|through)?\s*Telegram|"
    r"message\s+(?:on|via|through)?\s*WhatsApp\s+to\s+confirm|"
    r"DM\s+on\s+Instagram|"
    r"send\s+payment\s+(?:on|via|through)?\s*Telegram|"
    r"contact\s+recruiter\s+via\s+Telegram\s+only|"
    r"apply\s+via\s+Telegram|"
    r"send\s+details\s+on\s+Telegram|"
    r"(?:on|via|through|in)\s+Telegram|"
    r"(?:on|via|through|in)\s+WhatsApp"
    r")\b",
    re.IGNORECASE,
)


UNSOLICITED_SELECTION_REGEX = re.compile(
    r"\b(?:"
    r"selected\s+without\s+applying|"
    r"we\s+found\s+your\s+profile\s+on|"
    r"you\s+have\s+been\s+selected|"
    r"congratulations\s+you\s+are\s+selected|"
    r"congratulations!?,?\s+you\s+have\s+been\s+selected|"
    r"offer\s+letter\s+attached|"
    r"job\s+confirmed"
    r")\b",
    re.IGNORECASE,
)

DOCUMENT_CLAIM_REGEX = re.compile(
    r"\b(?:"
    r"official\s+offer\s+letter|"
    r"appointment\s+letter\s+attached|"
    r"selection\s+letter|"
    r"government\s+certificate|"
    r"verified\s+offer"
    r")\b",
    re.IGNORECASE,
)


# -----------------------------------------------------------------------------
# 2. Rule Metadata Specifications
# -----------------------------------------------------------------------------

RULE_SPECS: Dict[str, dict] = {
    "SIG_UPFRONT_PAYMENT": {
        "signal_type": "financial_risk",
        "title": "Upfront Payment Requested",
        "description": "The opportunity explicitly requests fees, deposits, or monetary transfers before commencing work.",
        "severity": SignalSeverity.HIGH,
        "confidence": 0.95,
        "explanation": "Legitimate employers never ask jobseekers to pay registration, application, or training fees.",
    },
    "SIG_URGENCY_PRESSURE": {
        "signal_type": "urgency_coercion",
        "title": "Urgency and High-Pressure Language",
        "description": "Language pressuring immediate action, fee transfer, or claiming scarce remaining slots.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.90,
        "explanation": "Scammers often artificially create urgency to prevent candidates from verifying claims.",
    },
    "SIG_GUARANTEED_SELECTION": {
        "signal_type": "guarantee_anomaly",
        "title": "Guaranteed Employment / Placement Claim",
        "description": "Unrealistic promises of guaranteed hiring, placement, or 100% selection.",
        "severity": SignalSeverity.HIGH,
        "confidence": 0.95,
        "explanation": "Real employers assess qualifications; 100% guaranteed job offers without evaluation are common fraud indicators.",
    },
    "SIG_NO_INTERVIEW": {
        "signal_type": "recruitment_anomaly",
        "title": "Instant Hiring Without Interview",
        "description": "Claims of direct selection without evaluation, interview, or screening process.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.90,
        "explanation": "Authentic professional positions require at least a formal screening or interview.",
    },
    "SIG_NO_EXPERIENCE": {
        "signal_type": "recruitment_anomaly",
        "title": "Zero Experience or Qualifications Required",
        "description": "Advertising high compensation or guaranteed roles with explicitly zero qualifications.",
        "severity": SignalSeverity.LOW,
        "confidence": 0.80,
        "explanation": "While entry-level jobs exist, zero-experience offers paired with high pay are frequently predatory.",
    },
    "SIG_UNREALISTIC_EARNINGS": {
        "signal_type": "financial_risk",
        "title": "Unrealistic or Effortless Earnings Claim",
        "description": "Promises of outsized income for minimal hours or effortless remote tasks.",
        "severity": SignalSeverity.HIGH,
        "confidence": 0.95,
        "explanation": "Exaggerated earning claims (e.g. ₹1 lakh weekly for 1 hour/day) are hallmarks of task scams.",
    },
    "SIG_AUTHORITY_CLAIM": {
        "signal_type": "authority_claim",
        "title": "Government / Official Authority Claim",
        "description": "Mentions of government approval, ministry endorsement, or certified official affiliation.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.85,
        "explanation": "Scammers frequently invoke government names to gain unearned credibility with students.",
    },
    "SIG_INFORMAL_CONTACT_CHANNEL": {
        "signal_type": "contact_anomaly",
        "title": "Informal Messaging Channel Redirection",
        "description": "Directing recruitment, applications, or payments entirely through Telegram, WhatsApp, or Instagram.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.90,
        "explanation": "Corporate recruiters primarily use official domain emails; off-platform messaging facilitates unmonitored fraud.",
    },
    "SIG_PERSONAL_PAYMENT_DESTINATION": {
        "signal_type": "financial_risk",
        "title": "Personal Payment Handle / Account Destination",
        "description": "Payment instructions pointing to individual UPI addresses or private payment handles.",
        "severity": SignalSeverity.HIGH,
        "confidence": 0.95,
        "explanation": "Legitimate business transactions occur through verified merchant gateways, never personal VPAs.",
    },
    "SIG_UNSOLICITED_SELECTION": {
        "signal_type": "recruitment_anomaly",
        "title": "Unsolicited Selection Notice",
        "description": "Claims that the student was selected for a job they did not apply for.",
        "severity": SignalSeverity.MEDIUM,
        "confidence": 0.90,
        "explanation": "Phishing scams often announce selection out of the blue to pique candidate interest.",
    },
    "SIG_DOCUMENT_CLAIM": {
        "signal_type": "authority_claim",
        "title": "Formal Document / Offer Letter Claim",
        "description": "References to pre-issued official offer letters or selection certificates.",
        "severity": SignalSeverity.LOW,
        "confidence": 0.80,
        "explanation": "Offers issued prior to interviews or applications should be scrutinized carefully.",
    },
    "SIG_MULTIPLE_HIGH_RISK_PATTERNS": {
        "signal_type": "compound_risk",
        "title": "Multiple Severe Risk Patterns Detected",
        "description": "Co-occurrence of upfront payment demands, artificial urgency, and guaranteed hiring claims.",
        "severity": SignalSeverity.CRITICAL,
        "confidence": 0.98,
        "explanation": "The simultaneous presence of upfront fees, urgency, and guaranteed jobs strongly suggests high predatory risk.",
    },
}
