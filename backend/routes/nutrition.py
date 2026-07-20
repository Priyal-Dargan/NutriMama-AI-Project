"""
routes/nutrition.py
Nutrition tracker endpoints: log daily nutrients, view history, and log weight.
This is the Health Monitoring Agent's primary data source (wired in Phase 2).
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.nutrition import NutritionLog
from models.reports import WeightLog
from schemas.tracking import NutritionLogIn, NutritionLogOut, WeightLogIn, WeightLogOut
from utils.logger import get_logger

router = APIRouter(prefix="/nutrition", tags=["Nutrition Tracker"])
logger = get_logger(__name__)


@router.post("/log", response_model=NutritionLogOut, status_code=201)
def log_nutrition(
    payload: NutritionLogIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = NutritionLog(
        user_id=current_user.id,
        log_date=payload.log_date or date.today(),
        **payload.model_dump(exclude={"log_date"}),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(f"Nutrition logged: user_id={current_user.id} date={entry.log_date}")
    return entry


@router.get("/history", response_model=List[NutritionLogOut])
def nutrition_history(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(NutritionLog)
        .filter_by(user_id=current_user.id)
        .order_by(NutritionLog.log_date.desc())
        .limit(limit)
        .all()
    )


@router.post("/weight", response_model=WeightLogOut, status_code=201)
def log_weight(
    payload: WeightLogIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log_date = payload.log_date or date.today()

    # Compute weekly gain vs. the most recent prior entry, if one exists.
    previous = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == current_user.id, WeightLog.log_date < log_date)
        .order_by(WeightLog.log_date.desc())
        .first()
    )
    weekly_gain = round(payload.weight_kg - previous.weight_kg, 2) if previous else None

    entry = WeightLog(
        user_id=current_user.id,
        log_date=log_date,
        weight_kg=payload.weight_kg,
        notes=payload.notes,
        weekly_gain_kg=weekly_gain,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(f"Weight logged: user_id={current_user.id} weight={entry.weight_kg}kg")
    return entry


@router.get("/weight/history", response_model=List[WeightLogOut])
def weight_history(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(WeightLog)
        .filter_by(user_id=current_user.id)
        .order_by(WeightLog.log_date.desc())
        .limit(limit)
        .all()
    )
