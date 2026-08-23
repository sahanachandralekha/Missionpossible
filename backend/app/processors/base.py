"""Base abstraction for input processors in ScamCheck."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from backend.app.schemas.opportunity import OpportunityInput


class BaseInputProcessor(ABC):
    """Abstract base class for all input processors.
    
    Each processor handles format-specific validation and extraction (text normalization,
    image OCR, PDF parsing) and produces the common normalized OpportunityInput model.
    """

    @abstractmethod
    def validate(self, *args: Any, **kwargs: Any) -> bool:
        """Validate whether the incoming data satisfies format and safety requirements."""
        pass

    @abstractmethod
    def process(
        self,
        content: Any,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OpportunityInput:
        """Process format-specific raw data into a normalized OpportunityInput object."""
        pass
