"""Emotion detection router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import EmotionRequest, EmotionResult
from ..services import emotion_service

router = APIRouter(prefix="/api/emotion", tags=["emotion"])


@router.post("", response_model=EmotionResult)
def detect(req: EmotionRequest) -> EmotionResult:
    """Detect emotion from a piece of text.

    Returns the top label, confidence, and full probability distribution.
    Predictions are estimates and not psychological assessments.
    """
    try:
        result = emotion_service.detect(req.text)
        return EmotionResult(
            label=result["label"],
            confidence=result["confidence"],
            scores=result["scores"],
            note=result["note"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Emotion detection failed: {exc}") from exc


@router.get("/labels")
def labels() -> dict:
    """Return the supported canonical emotion labels."""
    return {
        "labels": emotion_service.ALL_LABELS,
        "engine": emotion_service.engine_status(),
        "note": emotion_service.NOTE,
    }
