"""
utils/ocr.py
Blood report text extraction. PDFs are read directly with PyPDF2 (most lab PDFs
are text-based, not scanned images); image uploads (JPG/PNG) go through
Tesseract OCR. Extracted raw text is then parsed with regex for four common
values (hemoglobin, ferritin, vitamin D, blood sugar/glucose).

This is intentionally conservative: regex extraction of lab values from
unstructured text is inherently unreliable (different labs format reports very
differently), so every extracted value is returned alongside the raw text and
the route layer always lets the user review/correct it before it's treated as
authoritative (per the spec: "allow manual correction before analysis").
"""

import os
import re
from typing import Optional, Dict

from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

from utils.logger import get_logger

logger = get_logger(__name__)

# Each pattern captures a numeric value near a common label for that analyte.
# Patterns are intentionally loose (labs format reports very inconsistently).
VALUE_PATTERNS = {
    "hemoglobin": r"h(?:a)?emoglobin\s*[:\-]?\s*(\d+\.?\d*)",
    "ferritin": r"ferritin\s*[:\-]?\s*(\d+\.?\d*)",
    "vitamin_d": r"vitamin\s*d(?:3)?\s*(?:\(?25[- ]?oh\)?)?\s*[:\-]?\s*(\d+\.?\d*)",
    "blood_sugar": r"(?:fasting\s*)?(?:blood\s*)?(?:glucose|sugar)\s*[:\-]?\s*(\d+\.?\d*)",
}


def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"PDF text extraction failed for {file_path}: {exc}")
            return ""

    if ext in (".png", ".jpg", ".jpeg"):
        try:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image)
        except Exception as exc:  # noqa: BLE001 — Tesseract binary may not be installed in all environments
            logger.error(f"OCR failed for {file_path}: {exc}")
            return ""

    logger.warning(f"Unsupported file type for extraction: {ext}")
    return ""


def parse_lab_values(raw_text: str) -> Dict[str, Optional[float]]:
    lowered = raw_text.lower()
    values: Dict[str, Optional[float]] = {}

    for field, pattern in VALUE_PATTERNS.items():
        match = re.search(pattern, lowered)
        values[field] = float(match.group(1)) if match else None

    return values


def analyze_blood_report(file_path: str) -> Dict:
    """
    Returns extracted lab values plus the raw OCR/PDF text (for user review) and
    a flag indicating whether extraction found anything usable, so the route
    layer can prompt for manual entry when it didn't.
    """
    raw_text = extract_text_from_file(file_path)
    values = parse_lab_values(raw_text)
    extracted_any = any(v is not None for v in values.values())

    return {
        "raw_text_preview": raw_text[:1000],
        "extracted_any_values": extracted_any,
        **values,
    }
