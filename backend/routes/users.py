"""
routes/users.py
Profile read/update endpoints — covers pregnancy profile, medical history, and
diet preferences in one combined GET/PUT pair (matches onboarding wizard's data shape).
"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models.user import User
from models.pregnancy import PregnancyProfile
from models.profile import MedicalHistory, DietPreferences
from schemas.profile import (
    PregnancyProfileIn,
    PregnancyProfileOut,
    MedicalHistoryIn,
    DietPreferencesIn,
    FullProfileOut,
)
from utils.pregnancy_calc import calculate_bmi, calculate_pregnancy_week, calculate_trimester
from utils.logger import get_logger

router = APIRouter(prefix="/profile", tags=["Profile"])
logger = get_logger(__name__)


def _list_to_text(value):
    return json.dumps(value) if value is not None else None


def _text_to_list(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        # Backward-compatible fallback for plain comma-separated strings
        return [v.strip() for v in value.split(",") if v.strip()]


@router.get("", response_model=FullProfileOut)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pregnancy = db.query(PregnancyProfile).filter_by(user_id=current_user.id).first()
    medical = db.query(MedicalHistory).filter_by(user_id=current_user.id).first()
    diet = db.query(DietPreferences).filter_by(user_id=current_user.id).first()

    pregnancy_out = None
    if pregnancy:
        pregnancy_out = PregnancyProfileOut(
            age=pregnancy.age,
            height_cm=pregnancy.height_cm,
            current_weight_kg=pregnancy.current_weight_kg,
            pre_pregnancy_weight_kg=pregnancy.pre_pregnancy_weight_kg,
            due_date=pregnancy.due_date,
            pregnancy_type=pregnancy.pregnancy_type,
            activity_level=pregnancy.activity_level,
            bmi=pregnancy.bmi,
            pregnancy_week=pregnancy.pregnancy_week,
            trimester=pregnancy.trimester,
        )

    medical_out = None
    if medical:
        medical_out = MedicalHistoryIn(
            diabetes=medical.diabetes,
            gestational_diabetes=medical.gestational_diabetes,
            hypertension=medical.hypertension,
            pcos=medical.pcos,
            thyroid=medical.thyroid,
            anemia=medical.anemia,
            lactose_intolerance=medical.lactose_intolerance,
            gluten_intolerance=medical.gluten_intolerance,
            allergies=_text_to_list(medical.allergies),
            other_conditions=medical.other_conditions,
        )

    diet_out = None
    if diet:
        diet_out = DietPreferencesIn(
            vegetarian=diet.vegetarian,
            vegan=diet.vegan,
            jain=diet.jain,
            eggetarian=diet.eggetarian,
            non_vegetarian=diet.non_vegetarian,
            cuisine=diet.cuisine,
            budget=diet.budget,
            favorite_foods=_text_to_list(diet.favorite_foods),
            disliked_foods=_text_to_list(diet.disliked_foods),
            available_ingredients=_text_to_list(diet.available_ingredients),
        )

    return FullProfileOut(pregnancy=pregnancy_out, medical=medical_out, diet=diet_out)


@router.put("/pregnancy", response_model=PregnancyProfileOut)
def update_pregnancy_profile(
    payload: PregnancyProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(PregnancyProfile).filter_by(user_id=current_user.id).first()
    if not profile:
        profile = PregnancyProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump().items():
        setattr(profile, field, value)

    # Derived fields — this is the same logic the User Profile Agent will use in Phase 2.
    profile.bmi = calculate_bmi(profile.current_weight_kg, profile.height_cm)
    profile.pregnancy_week = calculate_pregnancy_week(profile.due_date)
    profile.trimester = calculate_trimester(profile.pregnancy_week)

    db.commit()
    db.refresh(profile)
    logger.info(f"Pregnancy profile updated: user_id={current_user.id}")

    return PregnancyProfileOut(
        **payload.model_dump(),
        bmi=profile.bmi,
        pregnancy_week=profile.pregnancy_week,
        trimester=profile.trimester,
    )


@router.put("/medical", response_model=MedicalHistoryIn)
def update_medical_history(
    payload: MedicalHistoryIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(MedicalHistory).filter_by(user_id=current_user.id).first()
    if not record:
        record = MedicalHistory(user_id=current_user.id)
        db.add(record)

    data = payload.model_dump()
    record.diabetes = data["diabetes"]
    record.gestational_diabetes = data["gestational_diabetes"]
    record.hypertension = data["hypertension"]
    record.pcos = data["pcos"]
    record.thyroid = data["thyroid"]
    record.anemia = data["anemia"]
    record.lactose_intolerance = data["lactose_intolerance"]
    record.gluten_intolerance = data["gluten_intolerance"]
    record.allergies = _list_to_text(data["allergies"])
    record.other_conditions = data["other_conditions"]

    db.commit()
    logger.info(f"Medical history updated: user_id={current_user.id}")
    return payload


@router.put("/diet", response_model=DietPreferencesIn)
def update_diet_preferences(
    payload: DietPreferencesIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(DietPreferences).filter_by(user_id=current_user.id).first()
    if not record:
        record = DietPreferences(user_id=current_user.id)
        db.add(record)

    data = payload.model_dump()
    record.vegetarian = data["vegetarian"]
    record.vegan = data["vegan"]
    record.jain = data["jain"]
    record.eggetarian = data["eggetarian"]
    record.non_vegetarian = data["non_vegetarian"]
    record.cuisine = data["cuisine"]
    record.budget = data["budget"]
    record.favorite_foods = _list_to_text(data["favorite_foods"])
    record.disliked_foods = _list_to_text(data["disliked_foods"])
    record.available_ingredients = _list_to_text(data["available_ingredients"])

    db.commit()
    logger.info(f"Diet preferences updated: user_id={current_user.id}")
    return payload
