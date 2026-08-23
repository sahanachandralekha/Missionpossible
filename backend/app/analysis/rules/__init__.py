"""ScamCheck Rule-Based Signal Detection Package.

STATUS: FULLY IMPLEMENTED (Part 7)

Exports:
- RuleBasedSignalEngine: Core deterministic signal detector
- RULE_SPECS: Metadata specifications for all registered rules
"""

from backend.app.analysis.rules.rule_engine import RuleBasedSignalEngine
from backend.app.analysis.rules.rule_catalog import RULE_SPECS

__all__ = ["RuleBasedSignalEngine", "RULE_SPECS"]
