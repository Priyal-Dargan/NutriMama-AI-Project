"""
data/food_safety_table.py
Rule-based food safety classifications for common pregnancy food-safety questions.
Used by the Food Safety Agent for known foods (deterministic, citable, no
hallucination risk). Foods not in this table fall back to the LLM with a clear
lower-confidence label, and will eventually be backed by the RAG pipeline (Phase 3).

🟢 safe   🟡 moderation   🔴 avoid
"""

FOOD_SAFETY_TABLE = {
    "coffee": {
        "classification": "moderation",
        "explanation": "Caffeine is generally considered acceptable in pregnancy up to "
                        "about 200mg/day (roughly one 12oz cup of coffee). Higher intake "
                        "has been associated with increased miscarriage and low-birth-weight risk in observational studies.",
        "alternatives": ["Decaf coffee", "Herbal teas confirmed safe by your provider", "Roasted chicory \"coffee\""],
        "confidence": 0.85,
        "sources": ["ACOG Committee Opinion on Moderate Caffeine Consumption", "WHO antenatal care guidance"],
    },
    "papaya": {
        "classification": "avoid",
        "explanation": "Unripe or semi-ripe papaya contains high levels of latex and papain, "
                        "which have been linked to uterine contractions. Fully ripe papaya in small "
                        "amounts is considered lower-risk by some guidance, but many sources advise avoiding it entirely.",
        "alternatives": ["Ripe mango", "Ripe banana", "Melon"],
        "confidence": 0.75,
        "sources": ["Commonly cited maternal nutrition guidance (regional ICMR/government advisories)"],
    },
    "pineapple": {
        "classification": "moderation",
        "explanation": "Pineapple contains bromelain, which in very large quantities has been "
                        "theorized to soften the cervix, but normal food-portion consumption has "
                        "not been shown to cause harm. Moderate amounts are generally considered fine.",
        "alternatives": [],
        "confidence": 0.7,
        "sources": ["General maternal nutrition guidance"],
    },
    "paneer": {
        "classification": "safe",
        "explanation": "Paneer made from pasteurized milk is a safe, good source of protein and "
                        "calcium during pregnancy. Confirm it's made from pasteurized milk, "
                        "especially if store-bought from an unverified source.",
        "alternatives": [],
        "confidence": 0.9,
        "sources": ["FDA/USDA pasteurized dairy guidance for pregnancy"],
    },
    "raw eggs": {
        "classification": "avoid",
        "explanation": "Raw or undercooked eggs carry a Salmonella risk. Cook eggs until both "
                        "yolk and white are firm.",
        "alternatives": ["Fully cooked eggs", "Pasteurized egg products for recipes needing raw egg"],
        "confidence": 0.95,
        "sources": ["FDA food safety for pregnancy", "CDC Listeria/Salmonella pregnancy guidance"],
    },
    "soft cheese": {
        "classification": "avoid",
        "explanation": "Soft, mold-ripened cheeses (brie, camembert, blue cheese, queso fresco) "
                        "made from unpasteurized milk carry a Listeria risk. Versions clearly "
                        "labeled as made from pasteurized milk are considered safe.",
        "alternatives": ["Hard cheeses (cheddar, parmesan)", "Pasteurized soft cheeses"],
        "confidence": 0.9,
        "sources": ["FDA/CDC Listeria pregnancy guidance"],
    },
    "raw fish": {
        "classification": "avoid",
        "explanation": "Raw fish (sushi, sashimi) carries parasite and bacterial risk, and "
                        "pregnancy suppresses some immune responses that normally help fight these off.",
        "alternatives": ["Fully cooked fish", "Cooked sushi rolls (e.g. California roll)"],
        "confidence": 0.9,
        "sources": ["FDA seafood guidance for pregnancy"],
    },

    "shark": {
        "classification": "avoid",
        "explanation": "Shark is a high-mercury fish. Mercury accumulates in fetal "
                        "tissue and can affect developing nervous systems.",
        "alternatives": ["Salmon", "Shrimp", "Tilapia", "Canned light tuna"],
        "confidence": 0.9,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },
    "swordfish": {
        "classification": "avoid",
        "explanation": "Swordfish is a high-mercury fish and is advised against during pregnancy.",
        "alternatives": ["Salmon", "Shrimp", "Tilapia", "Canned light tuna"],
        "confidence": 0.9,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },
    "king mackerel": {
        "classification": "avoid",
        "explanation": "King mackerel is a high-mercury fish and is advised against during pregnancy.",
        "alternatives": ["Salmon", "Shrimp", "Tilapia", "Canned light tuna"],
        "confidence": 0.9,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },
    "tilefish": {
        "classification": "avoid",
        "explanation": "Tilefish is a high-mercury fish and is advised against during pregnancy.",
        "alternatives": ["Salmon", "Shrimp", "Tilapia", "Canned light tuna"],
        "confidence": 0.9,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },
    "tuna": {
        "classification": "moderation",
        "explanation": "Canned light tuna is lower in mercury and fine in moderation "
                        "(2-3 servings/week). Avoid albacore/bigeye tuna or tuna steaks, "
                        "which are higher in mercury.",
        "alternatives": ["Canned light tuna", "Salmon", "Shrimp"],
        "confidence": 0.8,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },
    "salmon": {
        "classification": "safe",
        "explanation": "Salmon is low in mercury and a good source of omega-3s when "
                        "fully cooked. Aim for 2-3 servings/week.",
        "alternatives": [],
        "confidence": 0.88,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },



    "seafood": {
        "classification": "moderation",
        "explanation": "Low-mercury seafood (salmon, shrimp, tilapia) cooked thoroughly is a good "
                        "source of omega-3s — aim for 2-3 servings/week. Avoid high-mercury fish "
                        "like shark, swordfish, king mackerel, and tilefish.",
        "alternatives": ["Salmon", "Shrimp", "Tilapia", "Cod"],
        "confidence": 0.85,
        "sources": ["FDA/EPA fish advice for pregnant women"],
    },
    "herbal teas": {
        "classification": "moderation",
        "explanation": "Safety varies a lot by herb. Ginger and peppermint tea are generally "
                        "considered fine in moderation. Many other herbal teas (e.g. those "
                        "containing licorice root, certain detox blends) lack safety data or "
                        "are best avoided — check with your provider before regular use.",
        "alternatives": ["Ginger tea", "Peppermint tea (in moderation)"],
        "confidence": 0.6,
        "sources": ["General maternal nutrition guidance — varies significantly by specific herb"],
    },
    "sushi": {
        "classification": "avoid",
        "explanation": "Traditional sushi made with raw fish carries parasite/bacterial risk. "
                        "Cooked sushi rolls are fine.",
        "alternatives": ["Cooked sushi rolls", "Vegetable rolls"],
        "confidence": 0.85,
        "sources": ["FDA seafood guidance for pregnancy"],
    },
    "alcohol": {
        "classification": "avoid",
        "explanation": "No amount of alcohol has been established as safe during pregnancy; it can "
                        "cause fetal alcohol spectrum disorders.",
        "alternatives": ["Mocktails", "Sparkling water with fruit"],
        "confidence": 0.97,
        "sources": ["CDC/ACOG alcohol-in-pregnancy guidance"],
    },
    "deli meat": {
        "classification": "moderation",
        "explanation": "Cold deli/lunch meats carry a Listeria risk unless heated until steaming "
                        "hot (165°F/74°C) right before eating.",
        "alternatives": ["Freshly cooked, hot meats", "Heated deli meat"],
        "confidence": 0.85,
        "sources": ["FDA/CDC Listeria pregnancy guidance"],
    },
}


def lookup_food(food_name: str):
    """
    Case-insensitive, trims whitespace. First tries an exact match, then falls
    back to checking whether any table key appears as a whole word inside the
    input (handles free-text chat messages like 'is raw salmon okay?' and
    simple plurals like 'sushis').
    """
    key = food_name.strip().lower()
    if key in FOOD_SAFETY_TABLE:
        return FOOD_SAFETY_TABLE[key]
    if key.endswith("s") and key[:-1] in FOOD_SAFETY_TABLE:
        return FOOD_SAFETY_TABLE[key[:-1]]

    import re
    for table_key, entry in FOOD_SAFETY_TABLE.items():
        if re.search ( r"\b" + re.escape(table_key) + r"\b", key ):
            return entry
    return None
