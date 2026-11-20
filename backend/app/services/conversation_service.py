"""High-level conversation orchestration: persist messages, detect emotion,
generate an emotion-aware reply, and return everything the API needs."""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .. import models
from . import emotion_service, llm_service

logger = logging.getLogger(__name__)


def _history_for_llm(messages: List[models.Message]) -> List[Dict[str, str]]:
    """Convert ORM messages to the simple dict the LLM service expects."""
    return [{"role": m.role, "content": m.content} for m in messages]


def _derive_title(text: str) -> str:
    """Auto-title a conversation from its first user message."""
    clean = " ".join(text.split())
    return (clean[:60] + "...") if len(clean) > 60 else clean or "New conversation"


def handle_user_message(
    db: Session,
    text: str,
    conversation_id: Optional[str],
    mode: str = "text",
) -> Dict[str, object]:
    """End-to-end handling of a single user turn.

    Returns a dict with: conversation_id, user_message_id,
    assistant_message_id, reply, emotion, emotion_confidence,
    emotion_scores, engine, note.
    """
    # 1. Resolve / create conversation.
    conversation: Optional[models.Conversation] = None
    if conversation_id:
        conversation = (
            db.query(models.Conversation)
            .filter(models.Conversation.id == conversation_id)
            .first()
        )
    if conversation is None:
        conversation = models.Conversation(
            title=_derive_title(text),
            mode=mode,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Persist user message.
    user_msg = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=text,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Detect emotion on the user's text.
    if models.get_setting(db, "emotion_detection_enabled", "true") == "false":
        scores = {label: 0.0 for label in emotion_service.ALL_LABELS}
        scores["neutral"] = 1.0
        emotion_result = {
            "label": "neutral",
            "confidence": 1.0,
            "scores": scores,
            "note": emotion_service.NOTE,
        }
    else:
        emotion_result = emotion_service.detect(text)
    user_msg.emotion = emotion_result["label"]
    user_msg.emotion_confidence = emotion_result["confidence"]
    user_msg.emotion_scores = json.dumps(emotion_result["scores"])
    db.commit()

    # 4. Build history for context (everything before this user message).
    prior = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation.id)
        .filter(models.Message.created_at < user_msg.created_at)
        .order_by(models.Message.created_at.asc())
        .all()
    )
    history = _history_for_llm(prior)

    # 5. Generate the assistant reply (emotion-aware).
    reply_text, engine = llm_service.generate_reply(
        text=text,
        emotion=emotion_result["label"],
        history=history,
    )

    assistant_msg = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=reply_text,
        # Assistant messages are tagged neutral by default - they are the
        # assistant's own tone, not a prediction about the user.
        emotion="neutral",
        emotion_confidence=1.0,
        emotion_scores=json.dumps({"neutral": 1.0}),
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # 6. Update conversation timestamp.
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "conversation_id": conversation.id,
        "user_message_id": user_msg.id,
        "assistant_message_id": assistant_msg.id,
        "reply": reply_text,
        "emotion": emotion_result["label"],
        "emotion_confidence": emotion_result["confidence"],
        "emotion_scores": emotion_result["scores"],
        "engine": engine,
        "note": emotion_result["note"],
    }
