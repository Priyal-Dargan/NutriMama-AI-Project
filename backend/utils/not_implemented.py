"""
utils/not_implemented.py
Shared helper for endpoints whose full implementation depends on the LangGraph
agents (Phase 2) or RAG pipeline (Phase 3), which haven't been built yet.

These routes are registered NOW so the API surface, Swagger docs, and frontend
can be wired against a stable contract from day one — they just return 501 with
a clear explanation instead of pretending to work. This is intentional and is
called out in README.md under "Build Status".
"""

from fastapi import HTTPException, status


def not_implemented(feature: str, phase: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"'{feature}' is not implemented yet — scheduled for {phase}. See README.md Build Status.",
    )
