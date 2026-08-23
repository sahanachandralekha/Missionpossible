"""Analysis Layer for ScamCheck.

STATUS: ARCHITECTURAL BOUNDARY (PLANNED)

This package will contain the analytical modules that consume normalized OpportunityInput:
- ML classification signals (analysis/ml/)
- Risk assessment and 0-100 score synthesis (analysis/risk/)
- Future heuristic, contact, and evidence extraction analyzers

Flow:
Normalized OpportunityInput -> Analysis Modules -> Risk Engine -> Explainable Risk Assessment
"""
