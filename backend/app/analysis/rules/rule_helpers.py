"""Helper utilities and negation detection for ScamCheck Rule-Based Signal Engine.

STATUS: FULLY IMPLEMENTED (Part 7)

Provides:
- Negation and context analysis (preventing false alarms on phrases like 'no registration fee')
- Substring boundary and contextual window extraction
- Standardized Evidence record instantiation
"""

import re
from typing import Any, Dict, Optional
from backend.app.analysis.models.evidence import Evidence


# Negation trigger regex (inspected before or immediately after a match)
NEGATION_PRE_REGEX = re.compile(
    r"\b(no|not|never|without|waived|do\s+not|don't|free\s+of|zero|neither|nor)\b",
    re.IGNORECASE,
)

NEGATION_POST_REGEX = re.compile(
    r"\b(is\s+not\s+required|not\s+needed|not\s+applicable|is\s+waived|is\s+free|is\s+optional)\b",
    re.IGNORECASE,
)


def is_negated(text: str, start: int, end: int, window: int = 45) -> bool:
    """Determine if a pattern match is negated in its immediate linguistic context.
    
    Examples:
    - 'No registration fee' -> True
    - 'Fee is not required' -> True
    - 'Do not pay any amount' -> True
    - 'Direct hiring without interview! Pay ₹1,500 training fee' -> False (negation in previous sentence)
    """
    raw_pre = text[max(0, start - window):start]
    boundary_pos = max(
        raw_pre.rfind("."),
        raw_pre.rfind("!"),
        raw_pre.rfind("?"),
        raw_pre.rfind("\n"),
        raw_pre.rfind(";"),
    )
    if boundary_pos != -1:
        pre_window = raw_pre[boundary_pos + 1:]
    else:
        pre_window = raw_pre

    raw_post = text[end:min(len(text), end + window)]
    post_boundaries = [
        p for p in [
            raw_post.find("."),
            raw_post.find("!"),
            raw_post.find("?"),
            raw_post.find("\n"),
            raw_post.find(";"),
        ] if p != -1
    ]
    if post_boundaries:
        post_window = raw_post[:min(post_boundaries)]
    else:
        post_window = raw_post

    if NEGATION_PRE_REGEX.search(pre_window):
        return True

    if NEGATION_POST_REGEX.search(post_window):
        return True

    return False



def extract_context_window(text: str, start: int, end: int, window: int = 35) -> str:
    """Extract a clean surrounding context string for student explainability."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end].replace("\n", " ").strip()


def build_evidence(
    evidence_type: str,
    value: str,
    source: str,
    start: int,
    end: int,
    text: str,
    normalized_value: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Evidence:
    """Construct a traceable Evidence instance with character offsets and context window."""
    context = extract_context_window(text, start, end)
    return Evidence(
        type=evidence_type,
        value=value,
        source=source,
        location=f"offset:{start}-{end}",
        context=context,
        normalized_value=normalized_value or value,
        metadata=metadata or {},
    )
