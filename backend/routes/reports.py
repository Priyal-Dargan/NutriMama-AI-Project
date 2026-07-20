"""
routes/reports.py
Weekly/monthly nutrition + weight reports (built from real logged data), plus
blood report read/manual-correction endpoints. PDF export still depends on
Phase 4/5 frontend/deployment work.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.nutrition import NutritionLog
from models.reports import WeightLog, BloodReport
from utils.blood_report_explainer import explain_blood_report
from utils.not_implemented import not_implemented

router = APIRouter(prefix="/reports", tags=["Reports"])


def _aggregate(db: Session, user_id: int, days: int):
    since = date.today() - timedelta(days=days)
    logs = (
        db.query(NutritionLog)
        .filter(NutritionLog.user_id == user_id, NutritionLog.log_date >= since)
        .all()
    )
    weights = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user_id, WeightLog.log_date >= since)
        .order_by(WeightLog.log_date)
        .all()
    )

    n = max(len(logs), 1)
    return {
        "period_days": days,
        "average_calories": round(sum(l.calories for l in logs) / n, 1),
        "average_protein_g": round(sum(l.protein_g for l in logs) / n, 1),
        "average_iron_mg": round(sum(l.iron_mg for l in logs) / n, 1),
        "average_water_ml": round(sum(l.water_ml for l in logs) / n, 1),
        "weight_trend": [{"date": w.log_date, "weight_kg": w.weight_kg} for w in weights],
        "logged_days": len(logs),
    }


@router.get("/weekly")
def weekly_report(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _aggregate(db, current_user.id, 7)


@router.get("/monthly")
def monthly_report(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _aggregate(db, current_user.id, 30)


@router.get("/download")
def download_report(current_user: User = Depends(get_current_user)):
    not_implemented("PDF report export", "Phase 4/5")


# --- Blood Reports ----------------------------------------------------------

class BloodReportUpdate(BaseModel):
    hemoglobin: Optional[float] = None
    ferritin: Optional[float] = None
    vitamin_d: Optional[float] = None
    blood_sugar: Optional[float] = None


def _get_owned_report(report_id: int, user: User, db: Session) -> BloodReport:
    report = db.query(BloodReport).filter_by(id=report_id, user_id=user.id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blood report not found")
    return report


@router.get("/blood")
def list_blood_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reports = (
        db.query(BloodReport)
        .filter_by(user_id=current_user.id)
        .order_by(BloodReport.upload_date.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "upload_date": r.upload_date,
            "hemoglobin": r.hemoglobin,
            "ferritin": r.ferritin,
            "vitamin_d": r.vitamin_d,
            "blood_sugar": r.blood_sugar,
            "ai_summary": r.ai_summary,
        }
        for r in reports
    ]


@router.get("/blood/{report_id}")
def get_blood_report(
    report_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = _get_owned_report(report_id, current_user, db)
    return {
        "id": report.id,
        "upload_date": report.upload_date,
        "hemoglobin": report.hemoglobin,
        "ferritin": report.ferritin,
        "vitamin_d": report.vitamin_d,
        "blood_sugar": report.blood_sugar,
        "ai_summary": report.ai_summary,
        "doctor_recommendation": report.doctor_recommendation,
    }


@router.put("/blood/{report_id}")
def update_blood_report(
    report_id: int,
    payload: BloodReportUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manual correction of extracted values, per spec: 'allow manual correction
    before analysis.' Re-runs the AI explanation against the corrected values."""
    report = _get_owned_report(report_id, current_user, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(report, field, value)

    report.ai_summary = explain_blood_report(
        hemoglobin=report.hemoglobin,
        ferritin=report.ferritin,
        vitamin_d=report.vitamin_d,
        blood_sugar=report.blood_sugar,
    )
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "hemoglobin": report.hemoglobin,
        "ferritin": report.ferritin,
        "vitamin_d": report.vitamin_d,
        "blood_sugar": report.blood_sugar,
        "ai_summary": report.ai_summary,
    }
