"""
routes/mealplanner.py
Meal planner endpoints. /generate builds a graph state from the user's saved
profile/diet/nutrition data and runs the (now agentic) Meal Optimization Agent —
which itself retrieves blood reports, recent nutrition/weight logs, meal history,
and RAG-retrieved pregnancy nutrition knowledge before reasoning about the plan —
then persists the result. /history reads meal_history. /update and /delete are
full CRUD, unchanged.
"""

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.meals import MealHistory
from agents.profile_agent import run_profile_agent
from agents.nutrition_agent import run_nutrition_agent
from agents.meal_optimizer import generate_meal_plan
from utils.logger import get_logger

router = APIRouter(prefix="/mealplan", tags=["Meal Planner"])
logger = get_logger(__name__)

# Keys bundled into MealHistory.extended_json — everything the agentic planner
# produces beyond the six meal slots / shopping_list / ai_notes / three goal columns.
_EXTENDED_KEYS = [
    "iron_rich_foods", "calcium_rich_foods", "folic_acid_sources", "fiber_sources",
    "healthy_alternatives", "foods_to_avoid",
]


def _build_response(plan: dict, record_id=None, generation_date=None) -> dict:
    return {
        "id": record_id,
        "generation_date": generation_date,
        "breakfast": plan.get("breakfast"),
        "morning_snack": plan.get("morning_snack"),
        "lunch": plan.get("lunch"),
        "evening_snack": plan.get("evening_snack"),
        "dinner": plan.get("dinner"),
        "bedtime_snack": plan.get("bedtime_snack"),
        "shopping_list": plan.get("shopping_list", []),
        "ai_notes": plan.get("ai_notes"),
        "hydration_goal_ml": plan.get("hydration_goal_ml"),
        "calories_target": plan.get("calories_target"),
        "protein_goal_g": plan.get("protein_goal_g"),
        "iron_rich_foods": plan.get("iron_rich_foods", []),
        "calcium_rich_foods": plan.get("calcium_rich_foods", []),
        "folic_acid_sources": plan.get("folic_acid_sources", []),
        "fiber_sources": plan.get("fiber_sources", []),
        "healthy_alternatives": plan.get("healthy_alternatives", []),
        "foods_to_avoid": plan.get("foods_to_avoid", []),
        "deficiencies_addressed": plan.get("_deficiencies_addressed", []),
        "source": plan.get("_source"),
    }


@router.post("/generate", status_code=201)
def generate_meal_plan_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Build enough state for the Meal Optimizer without running the full chat graph.
    state = {"user_id": current_user.id, "user_message": "", "agent_execution_history": []}
    state = run_profile_agent(state, db)

    if not state.get("user_profile"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your pregnancy profile (PUT /profile/pregnancy) before generating a meal plan.",
        )

    state = run_nutrition_agent(state)
    plan = generate_meal_plan(state, db)  # agentic: retrieves blood reports/logs/history internally

    extended_bundle = {k: plan.get(k, []) for k in _EXTENDED_KEYS}
    extended_bundle["deficiencies_addressed"] = plan.get("_deficiencies_addressed", [])
    extended_bundle["meal_signature"] = plan.get("_meal_signature")
    extended_bundle["source"] = plan.get("_source")

    record = MealHistory(
        user_id=current_user.id,
        generation_date=date.today(),
        breakfast=json.dumps(plan.get("breakfast")),
        morning_snack=json.dumps(plan.get("morning_snack")),
        lunch=json.dumps(plan.get("lunch")),
        evening_snack=json.dumps(plan.get("evening_snack")),
        dinner=json.dumps(plan.get("dinner")),
        bedtime_snack=json.dumps(plan.get("bedtime_snack")),
        shopping_list=json.dumps(plan.get("shopping_list", [])),
        ai_notes=plan.get("ai_notes"),
        hydration_goal_ml=plan.get("hydration_goal_ml"),
        calories_target=plan.get("calories_target"),
        protein_goal_g=plan.get("protein_goal_g"),
        extended_json=json.dumps(extended_bundle),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(
        f"Meal plan generated: user_id={current_user.id} source={plan.get('_source')} "
        f"deficiencies_addressed={plan.get('_deficiencies_addressed')}"
    )

    return _build_response(plan, record_id=record.id, generation_date=record.generation_date)


@router.get("/history")
def meal_plan_history(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = (
        db.query(MealHistory)
        .filter_by(user_id=current_user.id)
        .order_by(MealHistory.generation_date.desc())
        .limit(limit)
        .all()
    )
    results = []
    for p in plans:
        extended = json.loads(p.extended_json) if p.extended_json else {}
        results.append({
            "id": p.id,
            "generation_date": p.generation_date,
            "breakfast": json.loads(p.breakfast) if p.breakfast else None,
            "morning_snack": json.loads(p.morning_snack) if p.morning_snack else None,
            "lunch": json.loads(p.lunch) if p.lunch else None,
            "evening_snack": json.loads(p.evening_snack) if p.evening_snack else None,
            "dinner": json.loads(p.dinner) if p.dinner else None,
            "bedtime_snack": json.loads(p.bedtime_snack) if p.bedtime_snack else None,
            "shopping_list": json.loads(p.shopping_list) if p.shopping_list else [],
            "ai_notes": p.ai_notes,
            "hydration_goal_ml": p.hydration_goal_ml,
            "calories_target": p.calories_target,
            "protein_goal_g": p.protein_goal_g,
            "iron_rich_foods": extended.get("iron_rich_foods", []),
            "calcium_rich_foods": extended.get("calcium_rich_foods", []),
            "folic_acid_sources": extended.get("folic_acid_sources", []),
            "fiber_sources": extended.get("fiber_sources", []),
            "healthy_alternatives": extended.get("healthy_alternatives", []),
            "foods_to_avoid": extended.get("foods_to_avoid", []),
            "deficiencies_addressed": extended.get("deficiencies_addressed", []),
            "source": extended.get("source"),
        })
    return results


@router.put("/update/{plan_id}")
def update_meal_plan(
    plan_id: int,
    slot: str,
    meal_json: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a single meal slot (e.g. swap breakfast) on an existing plan.
    `slot` must be one of the six meal fields; `meal_json` is a JSON-encoded meal object."""
    valid_slots = {"breakfast", "morning_snack", "lunch", "evening_snack", "dinner", "bedtime_snack"}
    if slot not in valid_slots:
        raise HTTPException(status_code=422, detail=f"slot must be one of {valid_slots}")

    plan = db.query(MealHistory).filter_by(id=plan_id, user_id=current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    setattr(plan, slot, meal_json)
    db.commit()
    logger.info(f"Meal plan slot updated: user_id={current_user.id} plan_id={plan_id} slot={slot}")
    return {"message": f"{slot} updated"}


@router.delete("/delete/{plan_id}", status_code=204)
def delete_meal_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = db.query(MealHistory).filter_by(id=plan_id, user_id=current_user.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")
    db.delete(plan)
    db.commit()