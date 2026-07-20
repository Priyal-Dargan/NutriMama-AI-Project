"""
agents/synthesizer.py
Merges the outputs of whichever specialist agents ran into a single, coherent
final_response string. This is orchestration/formatting, not generation from
scratch — the Supervisor never invents nutrition advice itself (per spec), it
only assembles what the specialist agents already produced.
"""

from agents.state import GraphState


def synthesize_response(state: GraphState) -> str:
    parts = []

    medical_guidance = state.get("medical_guidance")
    if medical_guidance:
        parts.append(medical_guidance.strip())

    food_safety = state.get("food_safety_results")
    if food_safety:
        parts.append(
            f"\n**Food Safety — {food_safety['food'].title()}** {food_safety['icon']} "
            f"({food_safety['classification'].title()})\n{food_safety['explanation']}"
        )
        if food_safety.get("alternatives"):
            parts.append(f"Alternatives: {', '.join(food_safety['alternatives'])}")

    requirements = state.get("nutrition_requirements")
    if requirements and not state.get("meal_plan"):
        parts.append(
            f"\n**Your Daily Targets:** {requirements['calories']} kcal, "
            f"{requirements['protein_g']}g protein, {requirements['iron_mg']}mg iron, "
            f"{requirements['calcium_mg']}mg calcium."
        )

    meal_plan = state.get("meal_plan")
    if meal_plan:
        plan_lines = ["\n**Today's Suggested Meal Plan:**"]
        for slot in ["breakfast", "morning_snack", "lunch", "evening_snack", "dinner", "bedtime_snack"]:
            meal = meal_plan.get(slot)
            if meal:
                plan_lines.append(f"- {slot.replace('_', ' ').title()}: {meal['name']} ({meal['calories']} kcal)")
        if meal_plan.get("ai_notes"):
            plan_lines.append(f"\n_Why this plan:_ {meal_plan['ai_notes']}")
        parts.append("\n".join(plan_lines))

    health_insights = state.get("health_insights")
    if health_insights:
        parts.append(f"\n**Health Monitoring:** {health_insights['summary']}")
        for flag in health_insights.get("flags", []):
            parts.append(f"- {flag}")

    suggested_reminders = state.get("suggested_reminders")
    if suggested_reminders:
        parts.append(
            f"\nI can also set up {len(suggested_reminders)} suggested reminders "
            "(water, prenatal vitamin, etc.) — let me know if you'd like me to add them."
        )

    if not parts:
        parts.append(
            "I wasn't able to generate a specific recommendation for that yet. "
            "Could you tell me more about what you'd like help with — a meal plan, "
            "checking if a food is safe, or general nutrition guidance?"
        )

    return "\n".join(parts)
