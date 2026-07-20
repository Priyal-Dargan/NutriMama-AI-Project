"""
models/meals.py
Generated meal plans. Each row is one meal-plan generation for a given date;
the individual meal slots are stored as JSON text (slot name -> {recipe, ingredients, macros}).

Agentic Meal Planner addition (meal-planner-specific, additive only):
four nullable columns were added so the Meal Optimization Agent can persist the
extra personalized targets/context it now reasons over (hydration/calorie/protein
goals, and a JSON bundle of micronutrient food lists + per-user reasoning +
a "signature" of the plan used to keep future generations varied). Nothing about
the existing columns changed, so every other module reading MealHistory keeps working.
"""

from datetime import datetime, date

from sqlalchemy import Column, Integer, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base
from utils.logger import get_logger

logger = get_logger(__name__)


class MealHistory(Base):
    __tablename__ = "meal_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    generation_date = Column(Date, default=date.today, nullable=False)

    # Each stored as JSON text: {"name": ..., "calories": ..., "protein": ..., "recipe": ...,
    # "ingredients": [...], "prep_time_minutes": ..., "estimated_cost": ..., "why_recommended": ...}
    breakfast = Column(Text, nullable=True)
    morning_snack = Column(Text, nullable=True)
    lunch = Column(Text, nullable=True)
    evening_snack = Column(Text, nullable=True)
    dinner = Column(Text, nullable=True)
    bedtime_snack = Column(Text, nullable=True)

    shopping_list = Column(Text, nullable=True)   # JSON array
    ai_notes = Column(Text, nullable=True)         # explanation / "why this recommendation"

    # --- Added for the Agentic Meal Planner (Meal Optimization Agent v2) ---
    hydration_goal_ml = Column(Integer, nullable=True)
    calories_target = Column(Integer, nullable=True)
    protein_goal_g = Column(Integer, nullable=True)
    # JSON text bundle: {"iron_rich_foods": [...], "calcium_rich_foods": [...],
    # "folic_acid_sources": [...], "fiber_sources": [...], "healthy_alternatives": [...],
    # "foods_to_avoid": [...], "deficiencies_addressed": [...], "meal_signature": "...",
    # "source": "ai_generated" | "template_fallback"}
    extended_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="meal_history")


def ensure_meal_history_schema(engine) -> None:
    """
    Idempotent, additive-only migration for the four columns above.
    Base.metadata.create_all() only creates tables that don't exist yet — it never
    ALTERs an existing SQLite table — so a database created before this change needs
    these columns added by hand once. Safe to call on every startup: it inspects
    the actual columns first and only issues ALTER TABLE for whatever is missing.
    Only runs for SQLite (this project's only supported database_url); on any other
    backend it logs and no-ops, deferring to a real migration tool (e.g. Alembic).
    """
    if engine.dialect.name != "sqlite":
        logger.info("ensure_meal_history_schema: non-SQLite engine detected, skipping (use a real migration tool).")
        return

    new_columns = {
        "hydration_goal_ml": "INTEGER",
        "calories_target": "INTEGER",
        "protein_goal_g": "INTEGER",
        "extended_json": "TEXT",
    }

    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(meal_history)").fetchall()}
        if not existing:
            return  # table doesn't exist yet -- create_all() will create it with the new columns already included
        for column_name, column_type in new_columns.items():
            if column_name not in existing:
                conn.exec_driver_sql(f"ALTER TABLE meal_history ADD COLUMN {column_name} {column_type}")
                logger.info(f"ensure_meal_history_schema: added column meal_history.{column_name}")