"""
models/profile.py
Extended profile data: medical conditions/allergies and dietary preferences.
Kept separate from PregnancyProfile so each agent only touches the table it owns.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    diabetes = Column(Boolean, default=False)
    gestational_diabetes = Column(Boolean, default=False)
    hypertension = Column(Boolean, default=False)
    pcos = Column(Boolean, default=False)
    thyroid = Column(Boolean, default=False)
    anemia = Column(Boolean, default=False)
    lactose_intolerance = Column(Boolean, default=False)
    gluten_intolerance = Column(Boolean, default=False)

    allergies = Column(Text, nullable=True)        # comma-separated or JSON-encoded list
    other_conditions = Column(Text, nullable=True)  # free text for anything not covered above

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="medical_history")


class DietPreferences(Base):
    __tablename__ = "diet_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    vegetarian = Column(Boolean, default=False)
    vegan = Column(Boolean, default=False)
    jain = Column(Boolean, default=False)
    eggetarian = Column(Boolean, default=False)
    non_vegetarian = Column(Boolean, default=False)

    cuisine = Column(String(120), nullable=True)         # e.g. "North Indian", "South Indian"
    budget = Column(String(50), nullable=True)            # e.g. "low", "medium", "high"
    favorite_foods = Column(Text, nullable=True)
    disliked_foods = Column(Text, nullable=True)
    available_ingredients = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="diet_preferences")
