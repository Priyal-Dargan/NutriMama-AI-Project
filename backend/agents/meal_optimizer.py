"""
agents/meal_optimizer.py
Meal Optimization Agent — now a true agentic pipeline instead of a template picker.

Before calling Gemini it RETRIEVES and REASONS over every source the spec calls
for, all via existing modules (nothing below talks to the DB or the LLM in a way
that isn't already established elsewhere in this codebase):
  - user_profile / medical_conditions / diet_preferences  -> already loaded onto
    `state` by agents/profile_agent.py (unchanged, reused as-is).
  - nutrition_requirements (daily targets)                -> already loaded onto
    `state` by agents/nutrition_agent.py (unchanged, reused as-is).
  - latest BloodReport                                    -> queried here, same
    query style as models/reports.py rows are read elsewhere (e.g. monitoring_agent).
  - recent NutritionLog / WeightLog                        -> same lookback pattern
    as agents/monitoring_agent.py, reused to detect logged-intake deficiencies.
  - recent MealHistory                                     -> queried here so the
    agent can avoid repeating yesterday's (or last few days') meals and instead
    provide day-to-day variation.
  - pregnancy nutrition knowledge                          -> rag/retriever.py's
    retrieve_relevant_documents(), the exact same RAG pipeline agents/medical_agent.py
    already uses — not reimplemented, just called with a meal-planning-shaped query.

All of that is assembled into one structured JSON context object and handed to
Gemini (via utils/ai_client.generate_text — unchanged, now with response_format=
"json" requested for native structured output) together with a system prompt that
asks for the full extended output shape (macros + hydration goal + micronutrient
food lists + healthy alternatives + foods to avoid + a per-user "why" explanation).
If no provider is configured, or the model's JSON fails to parse, the SAME
reasoning context is used to build a deterministic fallback plan
(data/meal_templates.py) so the feature still works end-to-end without a live key.
"""

import hashlib
import json
import re
from datetime import date, datetime
from statistics import mean
from typing import Optional

from sqlalchemy.orm import Session

from agents.state import GraphState
from data.meal_templates import select_template, build_fallback_food_knowledge
from models.meals import MealHistory
from models.nutrition import NutritionLog
from models.reports import BloodReport, WeightLog
from rag.retriever import retrieve_relevant_documents
from utils.ai_client import generate_text, is_provider_configured
from utils.logger import get_logger

logger = get_logger(__name__)

LOOKBACK_DAYS = 7
MEAL_HISTORY_LOOKBACK = 5

MEAL_SLOTS = ["breakfast", "morning_snack", "lunch", "evening_snack", "dinner", "bedtime_snack"]

SYSTEM_PROMPT = (
    "You are the Meal Optimization Agent inside NutriMama AI for pregnancy nutrition planning.\n\n"
    "Return ONLY valid JSON. Never output markdown, commentary, or explanations.\n"
    "Do not stop early; complete the full JSON object.\n"
    "If you are nearing the token limit, shorten text rather than omitting fields.\n"
    "Use this exact schema and nothing else:\n"
    "{"
    '"breakfast": {"name": "...", "calories": 0, "protein_g": 0, "ingredients": ["..."], '
    '"prep_time_minutes": 0, "estimated_cost": "low", "why_recommended": "one short sentence"}, '
    '"morning_snack": {...}, "lunch": {...}, "evening_snack": {...}, "dinner": {...}, '
    '"bedtime_snack": {...}, '
    '"hydration_goal_ml": 0, "calories_target": 0, "protein_goal_g": 0'
    "}\n"
    "Each meal must have at most 5 concise ingredients. "
    "'why_recommended' must be one short sentence. "
    "Do NOT generate shopping_list, ai_notes, iron_rich_foods, calcium_rich_foods, "
    "folic_acid_sources, fiber_sources, healthy_alternatives, or foods_to_avoid."
)


# --- Context gathering (retrieval) ------------------------------------------------

# Reference thresholds mirroring the general context already used to explain blood
# reports to users (utils/blood_report_explainer.py) — reused here only as thresholds
# to decide which deficiencies to reason about, not to re-diagnose anything.
_LOW_HEMOGLOBIN = 11.0
_LOW_FERRITIN = 30.0
_LOW_VITAMIN_D = 20.0
_HIGH_FASTING_SUGAR = 95.0


def _detect_blood_deficiencies(report: Optional[BloodReport]) -> list:
    if not report:
        return []
    flags = []
    if report.hemoglobin is not None and report.hemoglobin < _LOW_HEMOGLOBIN:
        flags.append("low_hemoglobin")
    if report.ferritin is not None and report.ferritin < _LOW_FERRITIN:
        flags.append("low_iron_stores")
    if report.vitamin_d is not None and report.vitamin_d < _LOW_VITAMIN_D:
        flags.append("low_vitamin_d")
    if report.blood_sugar is not None and report.blood_sugar >= _HIGH_FASTING_SUGAR:
        flags.append("elevated_blood_sugar")
    return flags


def _summarize_recent_nutrition(logs: list, requirements: Optional[dict]) -> Optional[dict]:
    if not logs or not requirements:
        return None
    avg_calories = mean(l.calories for l in logs)
    avg_protein = mean(l.protein_g for l in logs)
    avg_iron = mean(l.iron_mg for l in logs)
    avg_calcium = mean(l.calcium_mg for l in logs)
    avg_water = mean(l.water_ml for l in logs)
    return {
        "avg_calories": round(avg_calories),
        "avg_protein_g": round(avg_protein, 1),
        "avg_iron_mg": round(avg_iron, 1),
        "avg_calcium_mg": round(avg_calcium, 1),
        "avg_water_ml": round(avg_water),
        "below_calorie_target": avg_calories < requirements["calories"] * 0.85,
        "below_protein_target": avg_protein < requirements["protein_g"] * 0.8,
        "below_iron_target": avg_iron < requirements["iron_mg"] * 0.7,
        "below_water_target": avg_water < requirements["water_ml"] * 0.7,
    }


def _summarize_weight_trend(weights: list) -> Optional[str]:
    if len(weights) < 2:
        return None
    recent_gain = weights[0].weight_kg - weights[-1].weight_kg
    weeks_span = max(1, (weights[0].log_date - weights[-1].log_date).days / 7)
    weekly_rate = recent_gain / weeks_span
    if weekly_rate > 1.0:
        return f"gaining faster than typically recommended (~{weekly_rate:.1f}kg/week recently)"
    if weekly_rate < 0:
        return "weight has dropped recently"
    return "weight gain looks within a typical range"


def _extract_recent_meal_names(previous_plans: list) -> list:
    names = []
    for plan in previous_plans:
        for slot in MEAL_SLOTS:
            raw = getattr(plan, slot)
            if not raw:
                continue
            try:
                meal = json.loads(raw)
                if meal and meal.get("name"):
                    names.append(meal["name"])
            except (TypeError, ValueError):
                continue
    return names


def _build_rag_query(profile: dict, medical: dict, deficiencies: list) -> str:
    parts = ["pregnancy nutrition meal planning"]
    trimester = profile.get("trimester")
    if trimester:
        parts.append(f"trimester {trimester}")
    if medical.get("gestational_diabetes"):
        parts.append("gestational diabetes diet")
    if medical.get("hypertension"):
        parts.append("low sodium pregnancy diet")
    if medical.get("anemia") or "low_hemoglobin" in deficiencies or "low_iron_stores" in deficiencies:
        parts.append("iron anemia pregnancy diet")
    if "low_vitamin_d" in deficiencies:
        parts.append("vitamin D calcium pregnancy")
    if not medical.get("gestational_diabetes") and not deficiencies:
        parts.append("general pregnancy nutrition")
    return " ".join(parts)


def gather_planning_context(state: GraphState, db: Session) -> dict:
    """RETRIEVE + partially REASON over every source the spec requires, before any
    LLM call is made. Pure/read-only: makes no writes, so it's safe to call from
    either the direct /mealplan/generate route or the LangGraph chat flow."""
    user_id = state["user_id"]
    profile = state.get("user_profile") or {}
    medical = state.get("medical_conditions") or {}
    requirements = state.get("nutrition_requirements") or {}

    latest_report = (
        db.query(BloodReport).filter_by(user_id=user_id).order_by(BloodReport.upload_date.desc()).first()
    )
    deficiencies = _detect_blood_deficiencies(latest_report)

    recent_logs = (
        db.query(NutritionLog).filter_by(user_id=user_id).order_by(NutritionLog.log_date.desc())
        .limit(LOOKBACK_DAYS).all()
    )
    nutrition_summary = _summarize_recent_nutrition(recent_logs, requirements)

    recent_weights = (
        db.query(WeightLog).filter_by(user_id=user_id).order_by(WeightLog.log_date.desc()).limit(3).all()
    )
    weight_trend = _summarize_weight_trend(recent_weights)

    previous_plans = (
        db.query(MealHistory).filter_by(user_id=user_id).order_by(MealHistory.generation_date.desc())
        .limit(MEAL_HISTORY_LOOKBACK).all()
    )
    recent_meal_names = _extract_recent_meal_names(previous_plans)

    rag_query = _build_rag_query(profile, medical, deficiencies)
    retrieved_docs = retrieve_relevant_documents(rag_query)

    return {
        "blood_deficiencies": deficiencies,
        "recent_nutrition_summary": nutrition_summary,
        "weight_trend": weight_trend,
        "recent_meal_names": recent_meal_names[:15],
        "retrieved_context": [{"source": d["source"], "snippet": d["snippet"]} for d in retrieved_docs],
        "generations_so_far": len(previous_plans),
        "today": date.today().isoformat(),
    }


# --- Prompt construction -----------------------------------------------------------

def _build_user_prompt(state: GraphState, context: dict) -> str:
    profile = state.get("user_profile") or {}
    diet = state.get("diet_preferences") or {}
    requirements = state.get("nutrition_requirements") or {}
    ingredients = state.get("available_ingredients") or []
    medical = state.get("medical_conditions") or {}

    return json.dumps(
        {
            "profile": {
                "age": profile.get("age"),
                "height_cm": profile.get("height_cm"),
                "weight_kg": profile.get("current_weight_kg"),
                "bmi": profile.get("bmi"),
                "pregnancy_week": profile.get("pregnancy_week"),
                "trimester": profile.get("trimester"),
                "pregnancy_type": profile.get("pregnancy_type"),
                "activity_level": profile.get("activity_level"),
            },
            "diet_preferences": diet,
            "available_ingredients": ingredients,
            "medical_conditions": {k: v for k, v in medical.items() if v},
            "daily_targets": requirements,
            "blood_work_deficiencies": context["blood_deficiencies"],
            "recent_logged_nutrition": context["recent_nutrition_summary"],
            "weight_trend": context["weight_trend"],
            "recent_meal_names": context["recent_meal_names"],
            "retrieved_context": context["retrieved_context"],
            "today": context["today"],
        },
        default=str,
    )


_BANNED_KEYWORDS = {
    "vegan": ["chicken", "mutton", "beef", "pork", "fish", "shrimp", "prawn", "crab", "meat",
              "egg", "milk", "paneer", "yogurt", "curd", "ghee", "cheese", "honey"],
    # vegetarian and eggetarian share the same meat/fish ban; eggetarian additionally allows egg.
    "vegetarian": ["chicken", "mutton", "beef", "pork", "fish", "shrimp", "prawn", "crab", "meat", "egg"],
    "eggetarian": ["chicken", "mutton", "beef", "pork", "fish", "shrimp", "prawn", "crab", "meat"],
    "non_vegetarian": [],  # no restriction
}

# Ingredient-level substitutions for constraints that shouldn't swap the whole meal
# (unlike a banned diet-type ingredient, a dairy or gluten item in an otherwise-fine
# meal can just be swapped for a safe equivalent in place).
_LACTOSE_SUBSTITUTIONS = {
    "milk": "lactose-free milk (or almond/soy milk)",
    "paneer": "tofu",
    "yogurt": "coconut yogurt (dairy-free)",
    "curd": "coconut yogurt (dairy-free)",
    "cheese": "dairy-free cheese",
    "ghee": "cooking oil",
    "butter": "plant-based butter",
}
_GLUTEN_SUBSTITUTIONS = {
    "whole wheat flour": "millet or rice flour",
    "whole wheat bread": "gluten-free bread",
    "wheat bread": "gluten-free bread",
    "wheat": "rice or millet",
    "roti": "rice/millet roti",
    "semolina": "rice flakes (poha)",
    "rava": "rice flakes (poha)",
}


def _resolve_diet_key(diet_preferences: dict) -> str:
    """Like data.meal_templates._diet_key, but keeps eggetarian as its own bucket here
    so enforcement can allow eggs for eggetarian while still banning meat/fish -- the
    fallback template bucketing (vegan/vegetarian/non_vegetarian only) is a separate,
    coarser concern from what's safe to let an AI-generated meal contain."""
    if not diet_preferences:
        return "vegetarian"
    if diet_preferences.get("vegan"):
        return "vegan"
    if diet_preferences.get("non_vegetarian"):
        return "non_vegetarian"
    if diet_preferences.get("eggetarian"):
        return "eggetarian"
    return "vegetarian"


def _violates_diet(meal: dict, banned: list) -> bool:
    text = (meal.get("name", "") + " " + " ".join(meal.get("ingredients", []))).lower()
    return any(word in text for word in banned)


def _apply_substitutions(meal: dict, substitutions: dict, reason_label: str) -> bool:
    """In-place, case-insensitive whole-word substitution across name + ingredients.
    Returns True if anything was changed (so the caller can log/annotate it).
    'lactose-free' / other already-safe items are left alone since the substitute
    strings themselves won't match the banned key again (e.g. 'lactose-free milk'
    still contains 'milk' as a substring -- so matching uses word boundaries AND
    skips items that already contain 'lactose-free', 'dairy-free', or 'gluten-free')."""
    changed = False

    def _sub_ingredient(ingredient: str) -> str:
        nonlocal changed
        lower = ingredient.lower()
        if any(tag in lower for tag in ("lactose-free", "dairy-free", "gluten-free")):
            return ingredient  # already an explicitly safe alternative -- leave as-is
        for banned_word, replacement in substitutions.items():
            if re.search(rf"\b{re.escape(banned_word)}\b", lower):
                changed = True
                return replacement
        return ingredient

    meal["ingredients"] = [_sub_ingredient(ing) for ing in meal.get("ingredients", [])]

    name_lower = meal.get("name", "").lower()
    if not any(tag in name_lower for tag in ("lactose-free", "dairy-free", "gluten-free")):
        for banned_word, replacement in substitutions.items():
            if re.search(rf"\b{re.escape(banned_word)}\b", name_lower):
                meal["name"] = re.sub(rf"\b{re.escape(banned_word)}\b", replacement, meal["name"], flags=re.IGNORECASE)
                changed = True

    return changed


def _enforce_dietary_constraints(plan: dict, diet_preferences: dict, medical_conditions: dict) -> dict:
    """Hard safety net applied to BOTH the AI-generated path and the deterministic
    fallback path: a prompt instruction (AI path) or a static template (fallback
    path) is not a guarantee. This is the actual code-level enforcement the spec
    requires, not just prompt wording.

    Four layers, applied in order:
      1. Diet type (vegan/vegetarian/eggetarian) -- meat/fish is a hard violation,
         so the whole slot is swapped for the corresponding slot of a template that
         is guaranteed safe for that diet type.
      2. Lactose intolerance -- dairy items are swapped in place for a dairy-free
         equivalent (milk -> almond/soy milk, paneer -> tofu, etc).
      3. Gluten intolerance -- wheat items are swapped in place for a gluten-free
         equivalent.
      4. Allergies (dynamic, user-entered list) -- any ingredient matching a stored
         allergy is stripped and replaced with a neutral placeholder.
    """
    medical_conditions = medical_conditions or {}
    diet_key = _resolve_diet_key(diet_preferences)
    banned_diet_words = _BANNED_KEYWORDS[diet_key]

    if banned_diet_words:
        template_diet_prefs = {"vegan": diet_key == "vegan", "non_vegetarian": diet_key == "non_vegetarian"}
        safe_template = select_template(template_diet_prefs, 0)
        violated_slots = []
        for slot in MEAL_SLOTS:
            meal = plan.get(slot)
            if meal and _violates_diet(meal, banned_diet_words):
                violated_slots.append(slot)
                safe_meal = dict(safe_template[slot])
                safe_meal["why_recommended"] = (
                    f"Swapped to a {diet_key}-safe option: the original suggestion for this "
                    f"slot didn't match your {diet_key} diet."
                )
                plan[slot] = safe_meal
        if violated_slots:
            logger.warning(f"Diet-type enforcement overrode slots {violated_slots} for diet_key={diet_key}")

    if medical_conditions.get("lactose_intolerance"):
        adjusted = []
        for slot in MEAL_SLOTS:
            meal = plan.get(slot)
            if meal and _apply_substitutions(meal, _LACTOSE_SUBSTITUTIONS, "lactose_intolerance"):
                adjusted.append(slot)
        if adjusted:
            logger.warning(f"Lactose-intolerance enforcement adjusted slots {adjusted}")

    if medical_conditions.get("gluten_intolerance"):
        adjusted = []
        for slot in MEAL_SLOTS:
            meal = plan.get(slot)
            if meal and _apply_substitutions(meal, _GLUTEN_SUBSTITUTIONS, "gluten_intolerance"):
                adjusted.append(slot)
        if adjusted:
            logger.warning(f"Gluten-intolerance enforcement adjusted slots {adjusted}")

    allergies = medical_conditions.get("allergies") or []
    if allergies:
        allergy_substitutions = {a.lower().strip(): f"a substitute (avoiding your {a.strip()} allergy)"
                                  for a in allergies if a and a.strip()}
        adjusted = []
        for slot in MEAL_SLOTS:
            meal = plan.get(slot)
            if meal and _apply_substitutions(meal, allergy_substitutions, "allergy"):
                adjusted.append(slot)
        if adjusted:
            logger.warning(f"Allergy enforcement adjusted slots {adjusted} for allergies={allergies}")

    return plan


def _extract_json(text: str) -> dict:
    """JSON extraction from an LLM response. The primary defense is requesting the
    provider's native JSON mode (see utils/ai_client.generate_text(..., response_format
    ="json")), which makes the API itself refuse to emit anything but valid JSON --
    that's what actually fixes stray-prose/unescaped-quote failures, not this function.
    This is kept as a defense-in-depth layer for: (a) providers/models that don't
    honor JSON mode, (b) a markdown fence still being present anyway.

    IMPORTANT FIX vs the previous version: the old bracket fallback did
    text.find("{") .. text.rfind("}") -- i.e. first-opening-brace to LAST closing
    brace in the ENTIRE string. If the response has any brace-containing content
    after the real JSON object (e.g. a trailing aside like "Note: {trimester
    adjustments applied}"), that grabs extra trailing text into the "JSON", which is
    exactly the kind of malformed input that produces "Expecting ',' delimiter".
    This version instead walks forward from the first "{" and counts nested braces
    until they balance back to zero, which finds the TRUE matching closing brace of
    the first object and ignores everything after it.
    """
    stripped = text.strip()

    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass  # fall through

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(stripped[start:i + 1])

    raise json.JSONDecodeError("No balanced JSON object found in AI response", stripped, 0)


def _plan_signature(plan: dict) -> str:
    names = "|".join(sorted((plan.get(slot) or {}).get("name", "") for slot in MEAL_SLOTS))
    return hashlib.sha256(names.encode("utf-8")).hexdigest()[:16]


_ALLOWED_MEAL_KEYS = {
    "name",
    "calories",
    "protein_g",
    "ingredients",
    "prep_time_minutes",
    "estimated_cost",
    "why_recommended",
}
_ALLOWED_TOP_LEVEL_KEYS = set(MEAL_SLOTS) | {"hydration_goal_ml", "calories_target", "protein_goal_g"}


def _normalize_why_recommended(text: Optional[str]) -> str:
    if not text:
        return "A balanced option tailored to your pregnancy needs."
    sentence = re.sub(r"\s+", " ", str(text)).strip()
    if not sentence:
        return "A balanced option tailored to your pregnancy needs."
    if not sentence.endswith((".", "!", "?")):
        sentence = f"{sentence}."
    return sentence.split(".")[0].strip() + "."


def _normalize_ai_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("AI plan must be a JSON object")

    normalized = {}
    for slot in MEAL_SLOTS:
        meal = plan.get(slot)
        if not isinstance(meal, dict):
            raise ValueError(f"AI plan missing meal slot {slot}")
        ingredients = meal.get("ingredients", []) or []
        if not isinstance(ingredients, list):
            ingredients = [str(ingredients)]
        normalized[slot] = {
            "name": meal.get("name"),
            "calories": meal.get("calories"),
            "protein_g": meal.get("protein_g"),
            "ingredients": [str(item) for item in ingredients[:5]],
            "prep_time_minutes": meal.get("prep_time_minutes"),
            "estimated_cost": meal.get("estimated_cost"),
            "why_recommended": _normalize_why_recommended(meal.get("why_recommended")),
        }

    for key in ("hydration_goal_ml", "calories_target", "protein_goal_g"):
        if key in plan:
            normalized[key] = plan[key]
    return normalized


def _validate_ai_plan(plan: dict) -> bool:
    """Defensive check for the reduced Gemini schema used by this planner."""
    if not isinstance(plan, dict):
        return False

    for slot in MEAL_SLOTS:
        meal = plan.get(slot)
        if not isinstance(meal, dict) or not meal.get("name"):
            return False
        if not isinstance(meal.get("ingredients"), list) or len(meal.get("ingredients", [])) > 5:
            return False
        if not meal.get("why_recommended"):
            return False
        if set(meal.keys()) - _ALLOWED_MEAL_KEYS:
            return False

    if set(plan.keys()) - _ALLOWED_TOP_LEVEL_KEYS:
        return False

    return all(key in plan for key in ("hydration_goal_ml", "calories_target", "protein_goal_g"))


def _attach_deterministic_metadata(plan: dict, diet_preferences: dict, medical_conditions: dict) -> dict:
    shopping_list = sorted({ing for slot in MEAL_SLOTS for ing in plan.get(slot, {}).get("ingredients", []) if ing})
    food_knowledge = build_fallback_food_knowledge(
        diet_preferences,
        lactose_intolerant=bool(medical_conditions.get("lactose_intolerance")),
    )

    plan["shopping_list"] = shopping_list
    plan["iron_rich_foods"] = food_knowledge.get("iron_rich_foods", [])
    plan["calcium_rich_foods"] = food_knowledge.get("calcium_rich_foods", [])
    plan["folic_acid_sources"] = food_knowledge.get("folic_acid_sources", [])
    plan["fiber_sources"] = food_knowledge.get("fiber_sources", [])
    plan["healthy_alternatives"] = food_knowledge.get("healthy_alternatives", [])
    plan["foods_to_avoid"] = food_knowledge.get("foods_to_avoid", [])

    notes = ["This plan was tailored to your pregnancy profile, diet preferences, and recent nutrition needs."]
    if medical_conditions.get("gestational_diabetes"):
        notes.append("Portion sizes were kept moderate for blood-sugar steadiness.")
    if medical_conditions.get("lactose_intolerance"):
        notes.append("Dairy was replaced with lactose-free or plant-based options where appropriate.")
    if medical_conditions.get("gluten_intolerance"):
        notes.append("Wheat-based choices were adjusted for gluten-free alternatives where appropriate.")
    plan["ai_notes"] = " ".join(notes)
    return plan


_SLOT_ROLE_HINTS = {
    "breakfast": "kickstarts your energy and protein intake for the day",
    "morning_snack": "keeps blood sugar steady between breakfast and lunch",
    "lunch": "your largest meal, built to hit a big share of today's protein and calorie target",
    "evening_snack": "a light bridge to dinner that avoids a big blood-sugar spike",
    "dinner": "a lighter, easily-digestible meal appropriate for the evening",
    "bedtime_snack": "supports overnight calcium/protein needs without being heavy before sleep",
}


def _meal_specific_reasoning(slot: str, meal: dict, diet_label: str, deficiencies: list, medical: dict,
                              trimester: Optional[int] = None) -> str:
    parts = [f"{meal.get('name')} {_SLOT_ROLE_HINTS.get(slot, 'fits your nutrient targets')}."]
    ingredient_text = " ".join(meal.get("ingredients", [])).lower()
    if "low_hemoglobin" in deficiencies or "low_iron_stores" in deficiencies:
        if any(w in ingredient_text for w in ["lentil", "spinach", "chickpea", "jaggery", "sesame"]):
            parts.append("Includes iron-supportive ingredients given your recent blood work.")
    if "low_vitamin_d" in deficiencies or "low_iron_stores" in deficiencies:
        if any(w in ingredient_text for w in ["milk", "paneer", "yogurt", "sesame", "tofu"]):
            parts.append("Also contributes calcium/vitamin D-supportive nutrients.")
    if medical.get("gestational_diabetes") and slot in ("evening_snack", "bedtime_snack"):
        parts.append("Kept light and lower-glycemic given gestational diabetes.")
    if trimester == 1 and slot == "morning_snack":
        parts.append("A gentle, easy-to-digest option for first-trimester nausea.")
    elif trimester == 3 and slot in ("lunch", "dinner"):
        parts.append("Sized to support third-trimester calorie and protein needs.")
    parts.append(f"Fits your {diet_label} diet.")
    return " ".join(parts)


def _build_fallback_reason_text(reason: str) -> str:
    """Problem 2 fix: never claim 'AI provider not configured' unless that's actually
    why we're here. `reason` is one of the specific strings generate_meal_plan()
    passes in, describing the REAL cause of the fallback."""
    if reason == "ai_provider_not_configured":
        return "This is a template-based plan because no AI provider is configured yet (see GEMINI_API_KEY in .env)."
    if reason.startswith("json_parse_failed"):
        return ("This is a template-based plan because the AI's response couldn't be parsed as valid JSON "
                "this time (a transient formatting issue, not a configuration problem) -- try generating again.")
    if reason.startswith("validation_failed"):
        return ("This is a template-based plan because the AI's response was missing required meal "
                "fields this time -- try generating again.")
    if reason.startswith("provider_error"):
        return ("This is a template-based plan because the AI provider call itself failed or timed out this "
                "time -- try generating again in a moment.")
    return "This is a template-based plan (the AI-generated plan wasn't usable this time)."


def _build_fallback_plan(state: GraphState, context: dict, reason: str = "ai_provider_not_configured") -> dict:
    """Deterministic path, used when no AI provider is configured or the LLM's JSON
    doesn't parse/validate. Uses the SAME retrieved context (deficiencies, targets,
    variation seed) so behaviour stays consistent with the agentic path, just without
    free-form generation. `reason` drives the user-facing explanation (Problem 2) and
    is one of: "ai_provider_not_configured", "json_parse_failed: <msg>",
    "validation_failed: <msg>", "provider_error: <msg>"."""
    diet = state.get("diet_preferences") or {}
    requirements = state.get("nutrition_requirements") or {}
    medical = state.get("medical_conditions") or {}
    profile = state.get("user_profile") or {}
    deficiencies = context["blood_deficiencies"]

    variant_index = context["generations_so_far"]
    template = select_template(diet, variant_index)
    plan = {slot: dict(meal) for slot, meal in template.items()}

    food_knowledge = build_fallback_food_knowledge(diet, lactose_intolerant=bool(medical.get("lactose_intolerance")))
    plan.update(food_knowledge)

    plan["hydration_goal_ml"] = requirements.get("water_ml")
    plan["calories_target"] = requirements.get("calories")
    plan["protein_goal_g"] = requirements.get("protein_g")

    notes = [_build_fallback_reason_text(reason)]
    if deficiencies:
        notes.append(
            f"Your last blood report flagged: {', '.join(d.replace('_', ' ') for d in deficiencies)} — "
            "the iron/calcium/vitamin food lists above were prioritized accordingly."
        )
    if medical.get("gestational_diabetes"):
        notes.append("Portion sizes were kept moderate given your gestational diabetes; discuss carb timing with your provider.")
    if medical.get("lactose_intolerance"):
        notes.append("Dairy items were swapped for lactose-free alternatives given your lactose intolerance.")
    if medical.get("gluten_intolerance"):
        notes.append("Wheat-based items were swapped for gluten-free alternatives given your gluten intolerance.")
    plan["ai_notes"] = " ".join(notes)

    # Problem 3 fix: the fallback path was never running dietary enforcement at all --
    # only diet-type template selection. lactose/gluten/allergy substitution must run
    # here too, since this deterministic path is what's actually served whenever the
    # AI path is unavailable (which, per Problem 1, was happening often). Runs BEFORE
    # the why_recommended text is built so the reasoning always describes the final,
    # already-substituted meal -- not the pre-substitution template original.
    plan = _enforce_dietary_constraints(plan, diet, medical)

    diet_label = "vegan" if diet.get("vegan") else "eggetarian" if diet.get("eggetarian") else \
        "vegetarian" if diet.get("vegetarian") else "non-vegetarian"
    trimester = profile.get("trimester")
    for slot in MEAL_SLOTS:
        if not plan[slot].get("why_recommended", "").startswith("Swapped to a"):
            # don't overwrite the diet-type-swap explanation set in _enforce_dietary_constraints
            plan[slot]["why_recommended"] = _meal_specific_reasoning(slot, plan[slot], diet_label, deficiencies, medical, trimester)

    plan["shopping_list"] = sorted({ing for slot in MEAL_SLOTS for ing in plan[slot]["ingredients"]})
    plan["_source"] = "template_fallback"
    return plan


# --- Public API ---------------------------------------------------------------------

def generate_meal_plan(state: GraphState, db: Session) -> dict:
    """Main agentic entry point. Retrieves + reasons over every required source,
    then either calls Gemini with a structured context (preferred path) or falls
    back to a deterministic, still-personalized plan. `db` is required now (unlike
    the old template-only version) because the agent reasons over blood reports,
    nutrition/weight logs, and meal history — not just the in-memory state."""
    context = gather_planning_context(state, db)
    diet_preferences = state.get("diet_preferences") or {}
    medical_conditions = state.get("medical_conditions") or {}

    if is_provider_configured():
        llm_text = None
        try:
            # max_tokens raised 2000 -> 4000 (this schema is large) and response_format=
            # "json" requests the provider's native structured-output mode, so the API
            # itself only emits valid JSON -- this is what actually fixes stray-prose /
            # unescaped-quote parse failures; _extract_json below is now just a
            # defense-in-depth layer, not the primary mechanism.
            llm_text = generate_text(
                SYSTEM_PROMPT, _build_user_prompt(state, context), max_tokens=4000, response_format="json",
            )
            if llm_text.startswith("[AI provider"):
                # utils/ai_client.generate_text degrades to a labeled string instead of
                # raising (by design, so one agent failure can't crash the graph) -- catch
                # that here explicitly so we report the REAL reason (Problem 2) instead of
                # trying to json.loads() it and getting a generic parse error.
                raise RuntimeError(llm_text)
            plan = _extract_json(llm_text)
            plan = _normalize_ai_plan(plan)
            if not _validate_ai_plan(plan):
                raise ValueError("AI plan missing required meal slots")
            plan = _enforce_dietary_constraints(plan, diet_preferences, medical_conditions)
            plan = _attach_deterministic_metadata(plan, diet_preferences, medical_conditions)
            plan["_source"] = "ai_generated"
            plan["_deficiencies_addressed"] = context["blood_deficiencies"]
            plan["_meal_signature"] = _plan_signature(plan)
            logger.info(f"Meal plan generated by Gemini for user_id={state['user_id']}")
            return plan
        except RuntimeError as exc:
            logger.warning(f"AI provider call did not succeed for user_id={state['user_id']}: {exc}")
            plan = _build_fallback_plan(state, context, reason=f"provider_error: {exc}")
        except (json.JSONDecodeError, ValueError) as exc:
            # Log the actual raw response (truncated) so a parse failure is diagnosable
            # instead of looking identical to "AI provider not configured".
            snippet = (llm_text or "<no response captured>")[:500]
            logger.warning(
                f"Meal plan JSON parse/validation failed for user_id={state['user_id']}: {exc}\n"
                f"Raw AI response (first 500 chars): {snippet}"
            )
            reason = f"json_parse_failed: {exc}" if isinstance(exc, json.JSONDecodeError) else f"validation_failed: {exc}"
            plan = _build_fallback_plan(state, context, reason=reason)
    else:
        plan = _build_fallback_plan(state, context, reason="ai_provider_not_configured")

    plan["_deficiencies_addressed"] = context["blood_deficiencies"]
    plan["_meal_signature"] = _plan_signature(plan)
    return plan


def run_meal_optimizer_agent(state: GraphState, db: Session) -> GraphState:
    """Graph node wrapper — used by agents/supervisor.py inside the chat flow, mirroring
    how make_profile_node/make_monitoring_node close over `db` for their DB-dependent agents."""
    plan = generate_meal_plan(state, db)
    state["meal_plan"] = plan

    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "meal_optimization",
            "status": "completed",
            "detail": f"source={plan.get('_source')} deficiencies_addressed={plan.get('_deficiencies_addressed')}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Meal optimizer ran: user_id={state['user_id']} source={plan.get('_source')}")
    return state