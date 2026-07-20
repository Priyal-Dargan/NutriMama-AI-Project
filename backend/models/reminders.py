"""
models/reminders.py
User reminders (meals, water, supplements, exercise, sleep, appointments).
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    reminder_type = Column(String(50), nullable=False)  # meal, water, iron, calcium, vitamin, exercise, sleep, appointment
    title = Column(String(150), nullable=False)
    reminder_time = Column(Time, nullable=False)
    frequency = Column(String(50), default="daily")     # daily, weekly, once
    status = Column(String(20), default="active")        # active, completed, paused

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="reminders")
