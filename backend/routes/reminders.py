"""
routes/reminders.py
Full CRUD for reminders (meals, water, supplements, exercise, sleep, appointments).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.reminders import Reminder
from schemas.reminders import ReminderIn, ReminderUpdate, ReminderOut, REMINDER_TYPES
from utils.logger import get_logger

router = APIRouter(prefix="/reminder", tags=["Reminders"])
logger = get_logger(__name__)


def _get_owned_reminder(reminder_id: int, user: User, db: Session) -> Reminder:
    reminder = db.query(Reminder).filter_by(id=reminder_id, user_id=user.id).first()
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


@router.post("/create", response_model=ReminderOut, status_code=201)
def create_reminder(
    payload: ReminderIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.reminder_type not in REMINDER_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"reminder_type must be one of: {', '.join(sorted(REMINDER_TYPES))}",
        )

    reminder = Reminder(user_id=current_user.id, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    logger.info(f"Reminder created: user_id={current_user.id} type={reminder.reminder_type}")
    return reminder


@router.get("/list", response_model=List[ReminderOut])
def list_reminders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Reminder).filter_by(user_id=current_user.id).order_by(Reminder.reminder_time).all()


@router.put("/update/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = _get_owned_reminder(reminder_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    db.commit()
    db.refresh(reminder)
    logger.info(f"Reminder updated: user_id={current_user.id} reminder_id={reminder_id}")
    return reminder


@router.delete("/delete/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = _get_owned_reminder(reminder_id, current_user, db)
    db.delete(reminder)
    db.commit()
    logger.info(f"Reminder deleted: user_id={current_user.id} reminder_id={reminder_id}")
