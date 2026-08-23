"""Dedicated OCR (Optical Character Recognition) Service.

STATUS: IMPLEMENTED (Part 3)

Technology: RapidOCR (ONNX Runtime) + Pillow
- 100% Free, open-source, and locally runnable without cloud API keys or external binaries.
- Standalone ONNX runtime execution on CPU.
- Extracts text lines, bounding boxes, and confidence scores across English and multilingual Unicode.

Single Responsibility:
IMAGE BYTES -> DECODE & PREPROCESS -> OCR INFERENCE -> EXTRACTED TEXT & CONFIDENCE METADATA

Architectural Boundary:
Does NOT determine risk, classify scams, execute ML analysis, or verify URLs/companies.
"""

import io
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageOps


@dataclass
class OCRResult:
    """Structured extraction result from the OCR service."""
    text: str
    confidence_avg: Optional[float]
    line_count: int
    engine: str = "RapidOCR-ONNX"
    success: bool = True
    image_width: int = 0
    image_height: int = 0
    image_format: str = "UNKNOWN"


class OCRService:
    """Local OCR engine service for processing opportunity screenshots and image uploads."""

    def __init__(self, engine: Optional[Any] = None) -> None:
        self._engine = engine

    def _get_engine(self) -> Any:
        """Lazy-initialize the RapidOCR engine instance."""
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
        return self._engine

    def decode_and_validate_image(self, content: bytes) -> Tuple[Image.Image, Dict[str, Any]]:
        """Decode binary image bytes, validate format integrity, and extract image properties.
        
        Raises:
            ValueError: If the image content is empty, invalid, or corrupted.
        """
        if not content:
            raise ValueError("Uploaded image content is empty (0 bytes)")

        try:
            # Load image from bytes
            img = Image.open(io.BytesIO(content))
            img_format = img.format or "UNKNOWN"
            width, height = img.size

            if width <= 0 or height <= 0:
                raise ValueError("Uploaded image has invalid zero dimensions")

            # Handle RGBA / transparency by blending onto a clean white background
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                background = Image.new("RGBA", img.size, (255, 255, 255, 255))
                alpha_composite = Image.alpha_composite(background, img)
                rgb_img = alpha_composite.convert("RGB")
            else:
                rgb_img = img.convert("RGB")

            # Apply EXIF orientation if present
            rgb_img = ImageOps.exif_transpose(rgb_img) or rgb_img

            meta = {
                "width": width,
                "height": height,
                "format": img_format,
            }
            return rgb_img, meta

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Uploaded image is corrupted or cannot be decoded: {str(e)}")

    def preprocess_image(self, img: Image.Image) -> np.ndarray:
        """Perform light, non-destructive image preprocessing for OCR reliability."""
        # Convert PIL Image directly to RGB numpy array for ONNX inference
        img_np = np.array(img)
        return img_np

    def extract_text_from_bytes(self, content: bytes) -> OCRResult:
        """Extract text and confidence metadata from raw image bytes.
        
        Args:
            content: Raw binary bytes of the uploaded image.
            
        Returns:
            OCRResult with extracted text, average confidence score, and dimensions.
            
        Raises:
            ValueError: If image is corrupted, unreadable, or invalid.
        """
        rgb_img, img_meta = self.decode_and_validate_image(content)
        img_np = self.preprocess_image(rgb_img)

        engine = self._get_engine()
        ocr_response, _ = engine(img_np)

        if not ocr_response:
            # No text detected in image
            return OCRResult(
                text="",
                confidence_avg=None,
                line_count=0,
                engine="RapidOCR-ONNX",
                success=False,
                image_width=img_meta["width"],
                image_height=img_meta["height"],
                image_format=img_meta["format"],
            )

        # Parse detected lines and confidence scores
        extracted_lines: List[str] = []
        confidences: List[float] = []

        for item in ocr_response:
            # RapidOCR format: [ [box_coords], text, confidence_str ]
            if len(item) >= 3:
                line_text = str(item[1]).strip()
                try:
                    conf = float(item[2])
                    confidences.append(conf)
                except (ValueError, TypeError):
                    pass

                if line_text:
                    extracted_lines.append(line_text)

        consolidated_text = "\n".join(extracted_lines)
        avg_confidence = (
            round(sum(confidences) / len(confidences), 4)
            if confidences
            else None
        )

        return OCRResult(
            text=consolidated_text,
            confidence_avg=avg_confidence,
            line_count=len(extracted_lines),
            engine="RapidOCR-ONNX",
            success=bool(consolidated_text.strip()),
            image_width=img_meta["width"],
            image_height=img_meta["height"],
            image_format=img_meta["format"],
        )
