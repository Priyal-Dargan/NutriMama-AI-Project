"""
routes/upload.py
Blood report upload. File handling (validation, storage) plus real value
extraction (PyPDF2 for text PDFs, Tesseract OCR for images) and an AI-generated
plain-language explanation (never diagnostic). Extraction is best-effort —
regex-based extraction from unstructured lab report text is inherently
unreliable across different lab formats, so extracted values are always
editable via PUT /reports/blood/{id} before being treated as final.
"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from dependencies import get_current_user
from models.user import User
from models.reports import BloodReport
from utils.ocr import analyze_blood_report
from utils.blood_report_explainer import explain_blood_report
from utils.logger import get_logger

router = APIRouter(prefix="/upload", tags=["Uploads"])
logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/report", status_code=status.HTTP_201_CREATED)
async def upload_blood_report(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {ext} not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{current_user.id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Best-effort extraction — never blocks the upload if it fails.
    try:
        extraction = analyze_blood_report(file_path)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Blood report extraction failed: {exc}", exc_info=True)
        extraction = {"extracted_any_values": False, "hemoglobin": None, "ferritin": None,
                       "vitamin_d": None, "blood_sugar": None, "raw_text_preview": ""}

    ai_summary = None
    if extraction.get("extracted_any_values"):
        ai_summary = explain_blood_report(
            hemoglobin=extraction.get("hemoglobin"),
            ferritin=extraction.get("ferritin"),
            vitamin_d=extraction.get("vitamin_d"),
            blood_sugar=extraction.get("blood_sugar"),
        )

    report = BloodReport(
        user_id=current_user.id,
        file_path=file_path,
        hemoglobin=extraction.get("hemoglobin"),
        ferritin=extraction.get("ferritin"),
        vitamin_d=extraction.get("vitamin_d"),
        blood_sugar=extraction.get("blood_sugar"),
        ai_summary=ai_summary,
        doctor_recommendation=(
            "Always share your full report with your healthcare provider — "
            "automatic extraction may miss or misread values."
        ),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        f"Blood report uploaded: user_id={current_user.id} report_id={report.id} "
        f"extracted_values={extraction.get('extracted_any_values')}"
    )

    return {
        "id": report.id,
        "file_path": report.file_path,
        "upload_date": report.upload_date,
        "hemoglobin": report.hemoglobin,
        "ferritin": report.ferritin,
        "vitamin_d": report.vitamin_d,
        "blood_sugar": report.blood_sugar,
        "ai_summary": report.ai_summary,
        "extracted_any_values": extraction.get("extracted_any_values"),
        "message": (
            "Values extracted automatically where possible. Please review and correct "
            f"via PUT /reports/blood/{report.id} if anything looks wrong — automatic "
            "extraction from lab report formatting is not always perfectly reliable."
        ),
    }
