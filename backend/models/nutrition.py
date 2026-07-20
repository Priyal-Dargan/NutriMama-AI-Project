"""
models/nutrition.py
Daily nutrition tracking — what the Nutrition Planner / Health Monitoring agents read & write.
"""

from datetime import datetime, date

from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    log_date = Column(Date, default=date.today, nullable=False)

    calories = Column(Float, default=0)
    protein_g = Column(Float, default=0)
    iron_mg = Column(Float, default=0)
    calcium_mg = Column(Float, default=0)
    folate_mcg = Column(Float, default=0)
    vitamin_d_mcg = Column(Float, default=0)
    vitamin_b12_mcg = Column(Float, default=0)
    fiber_g = Column(Float, default=0)
    water_ml = Column(Float, default=0)

    meal_score = Column(Float, nullable=True)       # 0-100, how well meals matched targets
    nutrition_score = Column(Float, nullable=True)   # 0-100, overall daily nutrition adequacy

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="nutrition_logs")
