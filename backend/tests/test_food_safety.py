from data.food_safety_table import lookup_food
from agents.food_safety_agent import check_food_safety
from agents.intent import detect_intent


def test_exact_match():
    assert lookup_food("sushi")["classification"] == "avoid"

def test_fuzzy_match_sentence():
    assert lookup_food("is swordfish safe")["classification"] == "avoid"

def test_plural_match():
    assert lookup_food("sushis")["classification"] == "avoid"

def test_unknown_food_returns_none_from_table():
    assert lookup_food("xyzfood123") is None

def test_check_food_safety_grounded_for_known_food():
    result = check_food_safety("coffee")
    assert result["classification"] == "moderation"
    assert result["grounded"] is True

def test_intent_okay_phrasing():
    assert detect_intent("Is pineapple okay?") == "food_safety"

def test_intent_avoid_phrasing():
    assert detect_intent("Which fish should be avoided?") == "food_safety"