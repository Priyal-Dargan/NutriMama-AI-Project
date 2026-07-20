"""
database.py
SQLAlchemy engine/session setup for the SQLite database, plus a FastAPI
dependency (get_db) used by every route that needs DB access.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

# SQLite needs this connect_arg when used with multiple threads (FastAPI's default).
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and guarantees it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once at application startup."""
    # Import models here (not at module top) to avoid circular imports while
    # still registering every model with Base.metadata before create_all().
    import models.user            # noqa: F401
    import models.profile         # noqa: F401
    import models.pregnancy       # noqa: F401
    import models.nutrition       # noqa: F401
    import models.meals           # noqa: F401
    import models.reminders       # noqa: F401
    import models.reports         # noqa: F401
    import models.chat            # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Meal-planner-specific, additive-only schema patch (see models/meals.py) --
    # create_all() never ALTERs a pre-existing SQLite table, so a database file
    # created before the Agentic Meal Planner needs these columns added by hand.
    from models.meals import ensure_meal_history_schema
    ensure_meal_history_schema(engine)