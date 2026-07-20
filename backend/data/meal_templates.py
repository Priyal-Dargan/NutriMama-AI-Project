"""
data/meal_templates.py
Minimal deterministic fallback meal templates, used by the Meal Optimization Agent
only when no Generative AI provider is configured. This keeps /mealplan/generate
functional out of the box for testing/demos; once a real API key is set, the agent
generates fully personalized plans via the LLM instead of these templates.

Agentic Meal Planner addition: each diet type now has a second variant (B) so the
deterministic fallback also rotates day-to-day instead of repeating the exact same
plan every time, and a small deterministic micronutrient/food-knowledge table was
added so the fallback path can still populate iron/calcium/folate/fiber sources,
healthy alternatives, and foods-to-avoid (the AI-generated path fills these from
the LLM instead; see agents/meal_optimizer.py).
"""

VEGETARIAN_TEMPLATE = {
    "breakfast": {"name": "Vegetable poha with peanuts", "calories": 320, "protein_g": 8,
                  "ingredients": ["poha", "peanuts", "mixed vegetables", "mustard seeds", "turmeric"],
                  "prep_time_minutes": 20, "estimated_cost": "low"},
    "morning_snack": {"name": "Mixed nuts and a banana", "calories": 200, "protein_g": 6,
                       "ingredients": ["almonds", "walnuts", "banana"], "prep_time_minutes": 2,
                       "estimated_cost": "low"},
    "lunch": {"name": "Dal, rice, and spinach sabzi", "calories": 520, "protein_g": 18,
              "ingredients": ["lentils", "rice", "spinach", "ghee", "cumin"], "prep_time_minutes": 35,
              "estimated_cost": "low"},
    "evening_snack": {"name": "Roasted chana and fruit", "calories": 180, "protein_g": 8,
                       "ingredients": ["roasted chickpeas", "seasonal fruit"], "prep_time_minutes": 5,
                       "estimated_cost": "low"},
    "dinner": {"name": "Paneer curry with roti", "calories": 480, "protein_g": 22,
               "ingredients": ["paneer", "tomato", "whole wheat flour", "onion"], "prep_time_minutes": 30,
               "estimated_cost": "medium"},
    "bedtime_snack": {"name": "Warm milk with turmeric", "calories": 120, "protein_g": 7,
                       "ingredients": ["milk", "turmeric"], "prep_time_minutes": 5, "estimated_cost": "low"},
}

VEGAN_TEMPLATE = {
    "breakfast": {"name": "Vegetable upma with soy milk", "calories": 310, "protein_g": 8,
                  "ingredients": ["semolina or millet", "mixed vegetables", "soy milk"], "prep_time_minutes": 20,
                  "estimated_cost": "low"},
    "morning_snack": {"name": "Trail mix", "calories": 200, "protein_g": 6,
                       "ingredients": ["almonds", "raisins", "pumpkin seeds"], "prep_time_minutes": 2,
                       "estimated_cost": "low"},
    "lunch": {"name": "Chickpea and rice bowl with greens", "calories": 530, "protein_g": 20,
              "ingredients": ["chickpeas", "rice", "leafy greens", "olive oil"], "prep_time_minutes": 30,
              "estimated_cost": "low"},
    "evening_snack": {"name": "Hummus with carrot sticks", "calories": 190, "protein_g": 7,
                       "ingredients": ["chickpeas", "tahini", "carrots"], "prep_time_minutes": 10,
                       "estimated_cost": "low"},
    "dinner": {"name": "Tofu and vegetable stir-fry with quinoa", "calories": 470, "protein_g": 24,
               "ingredients": ["tofu", "mixed vegetables", "quinoa", "soy sauce"], "prep_time_minutes": 25,
               "estimated_cost": "medium"},
    "bedtime_snack": {"name": "Fortified soy milk", "calories": 110, "protein_g": 7,
                       "ingredients": ["fortified soy milk"], "prep_time_minutes": 1, "estimated_cost": "low"},
}

NON_VEGETARIAN_TEMPLATE = {
    "breakfast": {"name": "Egg bhurji with whole wheat toast", "calories": 350, "protein_g": 16,
                  "ingredients": ["eggs", "onion", "tomato", "whole wheat bread"], "prep_time_minutes": 15,
                  "estimated_cost": "low"},
    "morning_snack": {"name": "Greek yogurt with berries", "calories": 180, "protein_g": 12,
                       "ingredients": ["greek yogurt", "mixed berries"], "prep_time_minutes": 3,
                       "estimated_cost": "medium"},
    "lunch": {"name": "Grilled chicken with rice and vegetables", "calories": 560, "protein_g": 35,
              "ingredients": ["chicken breast", "rice", "mixed vegetables"], "prep_time_minutes": 35,
              "estimated_cost": "medium"},
    "evening_snack": {"name": "Boiled egg and fruit", "calories": 170, "protein_g": 9,
                       "ingredients": ["egg", "seasonal fruit"], "prep_time_minutes": 10,
                       "estimated_cost": "low"},
    "dinner": {"name": "Baked fish with sweet potato", "calories": 490, "protein_g": 30,
               "ingredients": ["salmon or tilapia", "sweet potato", "green beans"], "prep_time_minutes": 30,
               "estimated_cost": "medium"},
    "bedtime_snack": {"name": "Warm milk", "calories": 120, "protein_g": 8,
                       "ingredients": ["milk"], "prep_time_minutes": 2, "estimated_cost": "low"},
}


VEGETARIAN_TEMPLATE_B = {
    "breakfast": {"name": "Besan cheela with mint chutney", "calories": 300, "protein_g": 12,
                  "ingredients": ["gram flour", "onion", "tomato", "mint", "yogurt"], "prep_time_minutes": 20,
                  "estimated_cost": "low"},
    "morning_snack": {"name": "Sprouts salad", "calories": 170, "protein_g": 9,
                       "ingredients": ["mixed sprouts", "lemon", "cucumber", "tomato"], "prep_time_minutes": 5,
                       "estimated_cost": "low"},
    "lunch": {"name": "Rajma, brown rice, and beetroot salad", "calories": 540, "protein_g": 20,
              "ingredients": ["kidney beans", "brown rice", "beetroot", "onion", "cumin"], "prep_time_minutes": 40,
              "estimated_cost": "low"},
    "evening_snack": {"name": "Fruit chaat with roasted seeds", "calories": 190, "protein_g": 6,
                       "ingredients": ["seasonal fruit", "pumpkin seeds", "chaat masala"], "prep_time_minutes": 8,
                       "estimated_cost": "low"},
    "dinner": {"name": "Palak paneer with jeera rice", "calories": 500, "protein_g": 24,
               "ingredients": ["spinach", "paneer", "rice", "garlic", "cumin"], "prep_time_minutes": 30,
               "estimated_cost": "medium"},
    "bedtime_snack": {"name": "Warm milk with dates", "calories": 130, "protein_g": 6,
                       "ingredients": ["milk", "dates"], "prep_time_minutes": 5, "estimated_cost": "low"},
}

VEGAN_TEMPLATE_B = {
    "breakfast": {"name": "Millet porridge with fortified plant milk", "calories": 300, "protein_g": 9,
                  "ingredients": ["millet", "fortified soy or oat milk", "flaxseed", "banana"],
                  "prep_time_minutes": 15, "estimated_cost": "low"},
    "morning_snack": {"name": "Roasted chickpeas and orange", "calories": 190, "protein_g": 7,
                       "ingredients": ["roasted chickpeas", "orange"], "prep_time_minutes": 3,
                       "estimated_cost": "low"},
    "lunch": {"name": "Rajma and quinoa bowl with greens", "calories": 540, "protein_g": 22,
              "ingredients": ["kidney beans", "quinoa", "leafy greens", "sesame oil"], "prep_time_minutes": 35,
              "estimated_cost": "medium"},
    "evening_snack": {"name": "Peanut butter on whole wheat toast", "calories": 200, "protein_g": 8,
                       "ingredients": ["peanut butter", "whole wheat bread"], "prep_time_minutes": 3,
                       "estimated_cost": "low"},
    "dinner": {"name": "Lentil and vegetable curry with millet roti", "calories": 480, "protein_g": 22,
               "ingredients": ["lentils", "mixed vegetables", "millet flour"], "prep_time_minutes": 30,
               "estimated_cost": "low"},
    "bedtime_snack": {"name": "Fortified plant milk with a date", "calories": 115, "protein_g": 6,
                       "ingredients": ["fortified soy or oat milk", "dates"], "prep_time_minutes": 1,
                       "estimated_cost": "low"},
}

NON_VEGETARIAN_TEMPLATE_B = {
    "breakfast": {"name": "Oats and egg white omelette", "calories": 340, "protein_g": 20,
                  "ingredients": ["eggs", "oats", "spinach", "tomato"], "prep_time_minutes": 15,
                  "estimated_cost": "low"},
    "morning_snack": {"name": "Cottage cheese with fruit", "calories": 180, "protein_g": 14,
                       "ingredients": ["cottage cheese", "seasonal fruit"], "prep_time_minutes": 3,
                       "estimated_cost": "medium"},
    "lunch": {"name": "Fish curry with brown rice and greens", "calories": 550, "protein_g": 32,
              "ingredients": ["fish", "brown rice", "leafy greens", "coconut"], "prep_time_minutes": 35,
              "estimated_cost": "medium"},
    "evening_snack": {"name": "Roasted chana with a boiled egg", "calories": 190, "protein_g": 13,
                       "ingredients": ["roasted chickpeas", "egg"], "prep_time_minutes": 10,
                       "estimated_cost": "low"},
    "dinner": {"name": "Grilled chicken with quinoa and vegetables", "calories": 500, "protein_g": 34,
               "ingredients": ["chicken breast", "quinoa", "mixed vegetables"], "prep_time_minutes": 30,
               "estimated_cost": "medium"},
    "bedtime_snack": {"name": "Warm milk with a pinch of nutmeg", "calories": 120, "protein_g": 8,
                       "ingredients": ["milk", "nutmeg"], "prep_time_minutes": 2, "estimated_cost": "low"},
}

# Deterministic micronutrient/food-knowledge used to fill the extended output fields
# when no Generative AI provider is configured. Kept diet-aware (e.g. vegan gets
# plant-based calcium/iron sources) so the fallback still respects the user's diet type.
IRON_RICH_FOODS = {
    "vegan": ["lentils", "spinach", "pumpkin seeds", "fortified cereal", "dried apricots"],
    "vegetarian": ["lentils", "spinach", "jaggery", "chickpeas", "fortified cereal"],
    "non_vegetarian": ["lean red meat", "chicken liver", "eggs", "spinach", "lentils"],
}
CALCIUM_RICH_FOODS = {
    "vegan": ["sesame seeds (til)", "fortified plant milk", "tofu", "leafy greens", "almonds"],
    "vegetarian": ["milk", "paneer", "yogurt", "sesame seeds (til)", "leafy greens"],
    "non_vegetarian": ["milk", "yogurt", "paneer", "fish with edible bones", "leafy greens"],
}
FOLIC_ACID_SOURCES = ["leafy greens", "lentils", "chickpeas", "citrus fruits", "fortified cereal", "beetroot"]
FIBER_SOURCES = ["whole wheat", "oats", "brown rice", "fruits with skin", "vegetables", "lentils"]
HEALTHY_ALTERNATIVES = {
    "vegan": ["swap white rice for millets/quinoa", "swap regular milk for fortified soy/oat milk"],
    "vegetarian": ["swap white rice for brown rice", "swap fried snacks for roasted chana or nuts"],
    "non_vegetarian": ["swap red meat for fish or chicken more often", "swap white rice for brown rice"],
}
FOODS_TO_AVOID_GENERAL = [
    "raw or undercooked eggs/meat/fish", "unpasteurized dairy", "high-mercury fish (shark, swordfish, king mackerel)",
    "alcohol", "excess caffeine", "raw sprouts", "unwashed produce",
]


def _diet_key(diet_preferences: dict) -> str:
    if not diet_preferences:
        return "vegetarian"
    if diet_preferences.get("vegan"):
        return "vegan"
    # BUGFIX: eggetarian must NOT fall into the non_vegetarian bucket -- that group's
    # templates contain fish/chicken, which an eggetarian user must never receive.
    # Eggetarian is vegetarian + eggs; the vegetarian templates already contain no meat/
    # fish, so bucketing it there is correct and safe. Only an explicit non_vegetarian
    # flag should select the meat/fish templates.
    if diet_preferences.get("non_vegetarian"):
        return "non_vegetarian"
    return "vegetarian"


def select_template(diet_preferences: dict, variant_index: int = 0) -> dict:
    """variant_index rotates which of the (currently 2) templates per diet type is
    used, so back-to-back generations without an AI provider configured don't
    produce an identical plan every time."""
    diet_key = _diet_key(diet_preferences)
    templates = {
        "vegan": [VEGAN_TEMPLATE, VEGAN_TEMPLATE_B],
        "non_vegetarian": [NON_VEGETARIAN_TEMPLATE, NON_VEGETARIAN_TEMPLATE_B],
        "vegetarian": [VEGETARIAN_TEMPLATE, VEGETARIAN_TEMPLATE_B],
    }[diet_key]
    return templates[variant_index % len(templates)]


def build_fallback_food_knowledge(diet_preferences: dict, lactose_intolerant: bool = False) -> dict:
    """Fills the extended output fields deterministically for the template-fallback path.
    lactose_intolerant, if True, swaps in dairy-free calcium sources regardless of diet
    type (a vegetarian user who is also lactose intolerant should still not see milk/
    paneer/yogurt as their recommended calcium sources)."""
    diet_key = _diet_key(diet_preferences)
    calcium_sources = CALCIUM_RICH_FOODS["vegan"] if lactose_intolerant else CALCIUM_RICH_FOODS[diet_key]
    return {
        "iron_rich_foods": IRON_RICH_FOODS[diet_key],
        "calcium_rich_foods": calcium_sources,
        "folic_acid_sources": FOLIC_ACID_SOURCES,
        "fiber_sources": FIBER_SOURCES,
        "healthy_alternatives": HEALTHY_ALTERNATIVES[diet_key],
        "foods_to_avoid": FOODS_TO_AVOID_GENERAL,
    }