"""Chat router: emotion-aware message round-trip."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ChatRequest, ChatResponse
from ..services import conversation_service, emotion_service, llm_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Send a user message and receive an emotion-aware assistant reply.

    The endpoint:
      1. creates or reuses a conversation,
      2. stores the user message,
      3. runs emotion detection on the user text,
      4. generates an emotion-aware reply (rule engine, or OpenAI if a key
         is configured),
      5. stores the assistant message,
      6. returns everything the frontend needs to render the exchange.
    """
    try:
        result = conversation_service.handle_user_message(
            db=db,
            text=req.text,
            conversation_id=req.conversation_id,
            mode=req.mode,
        )
        return ChatResponse(
            conversation_id=result["conversation_id"],
            user_message_id=result["user_message_id"],
            assistant_message_id=result["assistant_message_id"],
            reply=result["reply"],
            emotion=result["emotion"],
            emotion_confidence=result["emotion_confidence"],
            emotion_scores=result["emotion_scores"],
            engine=result["engine"],
            note=result["note"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc


@router.get("/engines")
def engines() -> dict:
    """Report which emotion and chat engines are active."""
    return {
        "emotion_engine": emotion_service.engine_status(),
        "chat_engine": llm_service.active_engine(),
        "openai_configured": bool(__import__("os").getenv("OPENAI_API_KEY")),
    }
