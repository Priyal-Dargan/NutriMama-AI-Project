"""
models/reports.py
Weight tracking, blood report uploads/analysis, and user feedback.
"""

from datetime import datetime, date

from sqlalchemy import Column, Integer, Float, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class WeightLog(Base):
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    log_date = Column(Date, default=date.today, nullable=False)
    weight_kg = Column(Float, nullable=False)
    weekly_gain_kg = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weight_logs")


class BloodReport(Base):
    __tablename__ = "blood_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)

    hemoglobin = Column(Float, nullable=True)
    vitamin_d = Column(Float, nullable=True)
    ferritin = Column(Float, nullable=True)
    blood_sugar = Column(Float, nullable=True)

    ai_summary = Column(Text, nullable=True)
    doctor_recommendation = Column(Text, nullable=True)

    user = relationship("User", back_populates="blood_reports")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    rating = Column(Integer, nullable=True)  # 1-5
    feedback_text = Column(Text, nullable=True)
    feature_request = Column(Text, nullable=True)
    bug_report = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedback_entries")
