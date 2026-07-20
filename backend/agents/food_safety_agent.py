"""
agents/food_safety_agent.py
Food Safety Agent. Checks the curated lookup table first (deterministic, citable).
Only falls back to the LLM for foods not in the table, and clearly marks that
output as lower-confidence / RAG-grounded.
"""

import re
from datetime import datetime

from agents.state import GraphState
from data.food_safety_table import lookup_food
from utils.ai_client import generate_text
from utils.logger import get_logger

from rag.retriever import retrieve_relevant_documents, is_rag_index_ready

logger = get_logger(__name__)

CLASSIFICATION_EMOJI = {"safe": "🟢", "moderation": "🟡", "avoid": "🔴"}

SYSTEM_PROMPT = (
    "You are the Food Safety Agent inside NutriMama AI. Classify whether the named "
    "food is generally SAFE, should be consumed in MODERATION, or should be AVOIDED "
    "during pregnancy. Respond in this exact format:\n"
    "Classification: <safe|moderation|avoid>\n"
    "Explanation: <2-3 sentences, evidence-based reasoning>\n"
    "Alternatives: <comma-separated list, or 'none'>\n"
    "Be conservative when uncertain — prefer 'moderation' or 'avoid' over 'safe' if evidence is mixed."
)


def _extract_food_name(message: str) -> str:
    """
    Best-effort extraction of the food term from a natural-language chat message,
    so conversational phrasing doesn't get passed whole into lookup_food/RAG.
    Falls back to the trimmed original message if no pattern matches — this keeps
    old behavior intact for anything unexpected rather than failing loudly.
    """
    cleaned = message.strip().rstrip("?.!")
    patterns = [
        r"(?:is|are)\s+(.+?)\s+(?:safe|okay|ok|fine|allowed|harmful)",
        r"can i (?:eat|have|drink)\s+(.+)",
        r"should i avoid\s+(.+)",
        r"which\s+(.+?)\s+should\s+(?:be\s+)?avoided",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return cleaned

def _parse_llm_response(text: str) -> dict:
    classification_match = re.search(r"Classification:\s*(safe|moderation|avoid)", text, re.IGNORECASE)
    explanation_match = re.search(r"Explanation:\s*(.+?)(?:\nAlternatives:|$)", text, re.IGNORECASE | re.DOTALL)
    alternatives_match = re.search(r"Alternatives:\s*(.+)", text, re.IGNORECASE)

    classification = classification_match.group(1).lower() if classification_match else "moderation"
    explanation = explanation_match.group(1).strip() if explanation_match else text.strip()
    alternatives_raw = alternatives_match.group(1).strip() if alternatives_match else "none"
    alternatives = [] if alternatives_raw.lower() == "none" else [a.strip() for a in alternatives_raw.split(",")]

    return {"classification": classification, "explanation": explanation, "alternatives": alternatives}


def check_food_safety(food_name: str) -> dict:
    """Pure function — also used directly by routes/foodsafety.py without the full graph."""
    table_entry = lookup_food(food_name)

    if table_entry:
        return {
            "food": food_name,
            "classification": table_entry["classification"],
            "icon": CLASSIFICATION_EMOJI[table_entry["classification"]],
            "explanation": table_entry["explanation"],
            "alternatives": table_entry["alternatives"],
            "confidence": table_entry["confidence"],
            "sources": table_entry["sources"],
            "grounded": True,
            "source_type": "curated",
        }

# Not in curated table — retrieve grounded context before asking the LLM.
    documents = retrieve_relevant_documents(f"Is {food_name} safe during pregnancy?")

    if documents:
        context = "\n\n".join(f"[{d['source']}]: {d['snippet']}" for d in documents)
        user_prompt = f"Retrieved context:\n{context}\n\nFood: {food_name}"
        confidence = 0.75
        sources = sorted({d["source"] for d in documents})
        grounded = True
        source_type = "rag"

    elif is_rag_index_ready():
        user_prompt = f"No relevant documents found in the knowledge base.\n\nFood: {food_name}"
        confidence = 0.4
        sources = ["Not in curated database or knowledge base — general AI guidance. Confirm with your healthcare provider."]
        grounded = False
        source_type = "ai_only"
    else:
        user_prompt = f"Knowledge base not indexed.\n\nFood: {food_name}"
        confidence = 0.3
        sources = ["Not in curated database — knowledge base unavailable. Confirm with your healthcare provider."]
        grounded = False
        source_type = "ai_only"

    llm_text = generate_text(SYSTEM_PROMPT, user_prompt)
    parsed = _parse_llm_response(llm_text)
    return {
        "food": food_name,
        "classification": parsed["classification"],
        "icon": CLASSIFICATION_EMOJI.get(parsed["classification"], "🟡"),
        "explanation": parsed["explanation"],
        "alternatives": parsed["alternatives"],
        "confidence": confidence,
        "sources": sources,
        "grounded": grounded,
        "source_type": source_type,
    }


def run_food_safety_agent(state: GraphState) -> GraphState:
    # Extract a candidate food name from the message — naive heuristic for the
    # chat flow; the dedicated /foodsafety/check endpoint takes an explicit food_name.
    message = state["user_message"]
    food_name = _extract_food_name(message)
    result = check_food_safety(food_name)
    state["food_safety_results"] = result

    state.setdefault("confidence_scores", {})["food_safety"] = result["confidence"]
    state.setdefault("agent_execution_history", []).append(
        {
            "agent": "food_safety",
            "status": "completed",
            "detail": f"Classified as {result['classification']} (grounded={result['grounded']})",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    logger.info(f"Food safety agent ran: user_id={state['user_id']} grounded={result['grounded']}")
    return state
