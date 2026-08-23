"""ML & LLM Semantic Intelligence Module for ScamCheck.

STATUS: FULLY IMPLEMENTED (Part 11)

Exports:
- SemanticAnalyzer (Main semantic analysis orchestrator)
- SemanticModelProvider (Abstract provider interface)
- DeterministicSemanticProvider (Safe 100% offline fallback provider)
- MockSemanticProvider (Testing & diagnostic provider)
- SemanticModelOutput (Structured provider output schema)
- SemanticSignalItem (Structured provider signal item)
- get_semantic_provider (Provider factory)
"""

from backend.app.analysis.ml.base import SemanticModelProvider
from backend.app.analysis.ml.provider import (
    DeterministicSemanticProvider,
    MockSemanticProvider,
    get_semantic_provider,
)
from backend.app.analysis.ml.schemas import (
    SemanticModelOutput,
    SemanticSignalItem,
)
from backend.app.analysis.ml.semantic_analyzer import SemanticAnalyzer

__all__ = [
    "DeterministicSemanticProvider",
    "MockSemanticProvider",
    "SemanticAnalyzer",
    "SemanticModelOutput",
    "SemanticModelProvider",
    "SemanticSignalItem",
    "get_semantic_provider",
]
