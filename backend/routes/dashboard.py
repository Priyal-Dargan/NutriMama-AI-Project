"""
routes/dashboard.py
Aggregates today's nutrition, latest weight, and upcoming reminders for the dashboard.
Meal-plan summary will be added once the Meal Optimization Agent exists (Phase 2).
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.nutrition import NutritionLog
from models.reports import WeightLog
from models.reminders import Reminder
from utils.logger import get_logger

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = get_logger(__name__)


@router.get("")
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()

    today_logs = (
        db.query(NutritionLog)
        .filter_by(user_id=current_user.id, log_date=today)
        .all()
    )
    totals = {
        "calories": sum(l.calories for l in today_logs),
        "protein_g": sum(l.protein_g for l in today_logs),
        "iron_mg": sum(l.iron_mg for l in today_logs),
        "calcium_mg": sum(l.calcium_mg for l in today_logs),
        "water_ml": sum(l.water_ml for l in today_logs),
    }

    latest_weight = (
        db.query(WeightLog)
        .filter_by(user_id=current_user.id)
        .order_by(WeightLog.log_date.desc())
        .first()
    )

    upcoming_reminders = (
        db.query(Reminder)
        .filter_by(user_id=current_user.id, status="active")
        .order_by(Reminder.reminder_time)
        .limit(5)
        .all()
    )

    return {
        "today_nutrition": totals,
        "latest_weight_kg": latest_weight.weight_kg if latest_weight else None,
        "weight_log_date": latest_weight.log_date if latest_weight else None,
        "upcoming_reminders": [
            {
                "id": r.id,
                "title": r.title,
                "reminder_type": r.reminder_type,
                "reminder_time": r.reminder_time.strftime("%H:%M"),
            }
            for r in upcoming_reminders
        ],
        "today_meal_plan": None,  # populated once Meal Optimization Agent ships (Phase 2)
        "nutrition_score": None,  # populated once Health Monitoring Agent ships (Phase 2)
    }
