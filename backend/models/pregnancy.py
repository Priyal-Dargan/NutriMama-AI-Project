"""
models/pregnancy.py
Core pregnancy profile: age, anthropometrics, due date, trimester, activity level.
BMI/trimester/week are computed by the User Profile Agent, not stored as raw user input only.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class PregnancyProfile(Base):
    __tablename__ = "pregnancy_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    age = Column(Integer, nullable=False)
    height_cm = Column(Float, nullable=False)
    current_weight_kg = Column(Float, nullable=False)
    pre_pregnancy_weight_kg = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)  # computed: weight_kg / (height_m ** 2)

    pregnancy_week = Column(Integer, nullable=True)  # computed from due_date
    trimester = Column(Integer, nullable=True)  # 1, 2, or 3 — computed from pregnancy_week
    due_date = Column(Date, nullable=True)
    pregnancy_type = Column(String(50), default="singleton")  # singleton, twins, triplets...
    activity_level = Column(String(50), default="moderate")  # sedentary, light, moderate, active

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="pregnancy_profile")
