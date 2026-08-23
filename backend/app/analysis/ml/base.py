"""Abstract Provider Base Interface for ScamCheck Semantic Intelligence.

STATUS: FULLY IMPLEMENTED (Part 11)

Enforces strict vendor/model decoupling:
- Downstream orchestration interacts solely with SemanticModelProvider.
- Concrete providers (Deterministic fallback, Local ONNX/Transformers, Ollama, API endpoints)
  can be swapped seamlessly via configuration/injection without modifying AnalysisService.
"""

from abc import ABC, abstractmethod
from typing import Optional
from backend.app.analysis.models import AnalysisContext
from backend.app.analysis.ml.schemas import SemanticModelOutput


class SemanticModelProvider(ABC):
    """Abstract interface for all semantic analysis models and providers."""

    @abstractmethod
    def analyze(
        self,
        text: str,
        context: Optional[AnalysisContext] = None,
    ) -> SemanticModelOutput:
        """Execute semantic analysis on normalized opportunity text.
        
        Args:
            text: Normalized opportunity text string.
            context: Optional full AnalysisContext for entity/opportunity awareness.
            
        Returns:
            SemanticModelOutput: Structured output containing detected semantic signals.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the unique human-readable identifier for this provider."""
        pass
