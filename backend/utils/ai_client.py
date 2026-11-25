"""
utils/ai_client.py
Thin wrapper around Google Gemini / OpenAI so agents call one function regardless
of provider (config.AI_PROVIDER decides which). If no API key is configured, this
returns a clearly-labeled fallback instead of raising — this lets the LangGraph
workflow be fully exercised and tested (routing, state, DB writes) without a live
API key, while still being real integration code once a key is added.
"""

from typing import Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_PLACEHOLDER_VALUES = {"", "your-gemini-api-key-here", "your-openai-api-key-here"}


def is_provider_configured() -> bool:
    """Public check — used by agents that want to branch (e.g. fall back to a
    deterministic template) before even attempting a live call."""
    return _is_configured()


def _is_configured() -> bool:
    if settings.ai_provider == "gemini":
        return settings.gemini_api_key not in _PLACEHOLDER_VALUES
    if settings.ai_provider == "openai":
        return settings.openai_api_key not in _PLACEHOLDER_VALUES
    return False


def generate_text(system_prompt: str, user_prompt: str, max_tokens: int = 1024,
                   response_format: Optional[str] = None) -> str:
    """
    Calls the configured Generative AI provider. Returns the model's text response.
    On missing config or a provider error, returns a clearly-labeled fallback string
    rather than raising, so a single agent failure doesn't crash the whole graph —
    callers (agents) should still treat a fallback string as low-confidence.

    response_format: optional, pass "json" to request the provider's native
    structured-JSON output mode (Gemini's response_mime_type="application/json",
    OpenAI's response_format={"type": "json_object"}) instead of relying on prompt
    wording alone. Existing callers that don't pass this keep the exact previous
    behavior (free-form text), so this is fully backward compatible.
    """
    if not _is_configured():
        logger.warning(f"AI provider '{settings.ai_provider}' has no API key configured — using fallback.")
        return (
            "[AI provider not configured] Set GEMINI_API_KEY or OPENAI_API_KEY in .env "
            "to enable live generative responses. This is a placeholder so the rest of "
            "the system remains testable."
        )

    try:
        if settings.ai_provider == "gemini":
            return _call_gemini(system_prompt, user_prompt, max_tokens, response_format)
        elif settings.ai_provider == "openai":
            return _call_openai(system_prompt, user_prompt, max_tokens, response_format)
        else:
            return f"[Unknown AI provider '{settings.ai_provider}']"
    except Exception as exc:  # noqa: BLE001 — we deliberately want to degrade, not crash the graph
        logger.error(f"AI provider call failed: {exc}", exc_info=True)
        return (
            "[AI provider error] The generative AI call failed. Please try again shortly. "
            f"(provider={settings.ai_provider})"
        )


def _call_gemini(system_prompt: str, user_prompt: str, max_tokens: int,
                 response_format: Optional[str] = None) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"{system_prompt}\n\n{user_prompt}"

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    if response_format == "json":
        config.response_mime_type = "application/json"

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=config,
    )

    return response.text or ""


def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int,
                  response_format: Optional[str] = None) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    kwargs = {}
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs,
    )
    return response.choices[0].message.content