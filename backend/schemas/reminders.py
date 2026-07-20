"""
schemas/reminders.py
Pydantic models for reminder CRUD endpoints.
"""

from datetime import time as time_type
from typing import Optional

from pydantic import BaseModel, Field


REMINDER_TYPES = {"meal", "water", "iron", "calcium", "vitamin", "exercise", "sleep", "appointment"}


class ReminderIn(BaseModel):
    reminder_type: str = Field(..., description=f"One of: {', '.join(sorted(REMINDER_TYPES))}")
    title: str = Field(..., min_length=1, max_length=150)
    reminder_time: time_type
    frequency: str = "daily"


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    reminder_time: Optional[time_type] = None
    frequency: Optional[str] = None
    status: Optional[str] = None


class ReminderOut(ReminderIn):
    id: int
    status: str

    model_config = {"from_attributes": True}
