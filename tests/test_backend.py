"""Pytest suite for the EmotiVoice backend.

These tests use FastAPI's TestClient against the real app. Emotion detection
exercises the lexical fallback (or the HF model if available and cached) so
the suite passes offline.

Run from the backend/ directory:
    pip install -r requirements.txt
    pip install pytest
    pytest ../tests/ -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make backend/ importable when tests are run from the project root.
BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# Force the fallback engine + rule chat for deterministic, offline tests.
os.environ.setdefault("EMOTION_FALLBACK_ENABLED", "true")
os.environ.setdefault("CHAT_ENGINE", "rule")
os.environ.setdefault("OPENAI_API_KEY", "")
# Use an in-memory SQLite DB so tests don't touch the real file.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import engine, init_db, Base
from app.services import emotion_service, llm_service


@pytest.fixture(scope="module")
def client():
    """A TestClient with a fresh in-memory database."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


# ---------- Health ----------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"


# ---------- Emotion ----------
def test_emotion_labels(client):
    r = client.get("/api/emotion/labels")
    assert r.status_code == 200
    labels = r.json()["labels"]
    expected = {"joy", "sadness", "anger", "fear", "surprise", "neutral", "disgust"}
    assert set(labels) == expected


def test_emotion_detect_happy(client):
    r = client.post("/api/emotion", json={"text": "I am so happy and joyful today!"})
    assert r.status_code == 200
    body = r.json()
    assert body["label"] in emotion_service.ALL_LABELS
    assert 0.0 <= body["confidence"] <= 1.0
    assert sum(body["scores"].values()) == pytest.approx(1.0, abs=0.02)
    assert "estimates" in body["note"].lower()


def test_emotion_detect_sad(client):
    r = client.post("/api/emotion", json={"text": "I feel so sad and lonely and I want to cry"})
    assert r.status_code == 200
    # Lexical engine should at least put sad in the top 3.
    body = r.json()
    scores = body["scores"]
    top3 = sorted(scores, key=scores.get, reverse=True)[:3]
    assert "sadness" in top3


def test_emotion_empty_text_rejected(client):
    r = client.post("/api/emotion", json={"text": ""})
    assert r.status_code == 422  # Pydantic validation


# ---------- Chat ----------
def test_chat_creates_conversation(client):
    r = client.post("/api/chat", json={"text": "Hello there!", "mode": "text"})
    assert r.status_code == 200
    body = r.json()
    assert body["conversation_id"]
    assert body["reply"]
    assert body["emotion"] in emotion_service.ALL_LABELS
    assert body["engine"] in ("rule", "openai")
    # Subsequent message should reuse the same conversation.
    r2 = client.post("/api/chat", json={
        "text": "Tell me a joke",
        "conversation_id": body["conversation_id"],
        "mode": "text",
    })
    assert r2.status_code == 200
    assert r2.json()["conversation_id"] == body["conversation_id"]


def test_chat_voice_mode(client):
    r = client.post("/api/chat", json={"text": "I'm feeling great!", "mode": "voice"})
    assert r.status_code == 200
    assert r.json()["reply"]


# ---------- Conversations ----------
def test_conversation_lifecycle(client):
    # Create a conversation via chat.
    r = client.post("/api/chat", json={"text": "Hi, how are you?", "mode": "text"})
    cid = r.json()["conversation_id"]

    # List.
    lst = client.get("/api/conversations")
    assert lst.status_code == 200
    assert any(c["id"] == cid for c in lst.json()["conversations"])

    # Get with messages.
    one = client.get(f"/api/conversations/{cid}")
    assert one.status_code == 200
    assert len(one.json()["messages"]) >= 2  # user + assistant

    # Delete.
    d = client.delete(f"/api/conversations/{cid}")
    assert d.status_code == 200
    assert d.json()["deleted"] == cid

    # Confirm gone.
    assert client.get(f"/api/conversations/{cid}").status_code == 404


def test_clear_all(client):
    # Seed a couple of messages.
    client.post("/api/chat", json={"text": "one", "mode": "text"})
    client.post("/api/chat", json={"text": "two", "mode": "text"})
    r = client.post("/api/conversations/clear")
    assert r.status_code == 200
    assert r.json()["deleted_conversations"] >= 2


# ---------- Analytics ----------
def test_analytics(client):
    client.post("/api/chat", json={"text": "I am happy today!", "mode": "text"})
    client.post("/api/chat", json={"text": "I'm a bit worried", "mode": "text"})
    r = client.get("/api/analytics")
    assert r.status_code == 200
    body = r.json()
    assert body["total_conversations"] >= 2
    assert body["total_messages"] >= 4
    assert body["total_user_messages"] >= 2
    assert body["total_assistant_messages"] >= 2
    assert isinstance(body["emotion_distribution"], list)
    assert isinstance(body["recent_messages"], list)
    assert isinstance(body["daily_counts"], list)


# ---------- Settings ----------
def test_settings_get_default(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    keys = {s["key"] for s in r.json()["settings"]}
    assert "theme" in keys
    assert "auto_play_tts" in keys


def test_settings_update(client):
    r = client.put("/api/settings/theme", json={"key": "theme", "value": "light"})
    assert r.status_code == 200
    assert r.json()["value"] == "light"
    # Read back.
    g = client.get("/api/settings/theme")
    assert g.json()["value"] == "light"


def test_settings_reset(client):
    r = client.post("/api/settings/reset")
    assert r.status_code == 200
    assert r.json()["reset"] is True


# ---------- Voice info ----------
def test_voice_info(client):
    r = client.get("/api/voice/info")
    assert r.status_code == 200
    body = r.json()
    assert body["asr_engine"] == "web_speech_api"
    assert body["tts_engine"] == "web_speech_api"
    assert len(body["supported_emotions"]) == 7


def test_voice_labels_are_canonical(client):
    r = client.get("/api/voice/info")
    assert r.status_code == 200
    assert set(r.json()["supported_emotions"]) == {
        "joy", "sadness", "anger", "fear", "surprise", "neutral", "disgust"
    }


# ---------- Static frontend ----------
def test_index_html_served(client):
    r = client.get("/")
    assert r.status_code in (200, 307)


# ---------- LLM service unit ----------
def test_llm_rule_engine_varies():
    history = []
    replies = set()
    for _ in range(6):
        reply, engine = llm_service.generate_reply(
            "I'm feeling happy today!", emotion="joy", history=history
        )
        replies.add(reply)
        history.append({"role": "user", "content": "I'm feeling happy today!"})
        history.append({"role": "assistant", "content": reply})
    assert engine == "rule"
    # Should produce at least 2 distinct replies across 6 calls (no exact loop).
    assert len(replies) >= 2


# ---------- Emotion service unit ----------
def test_emotion_canonical_labels():
    res = emotion_service.detect("Wow that's amazing!")
    assert res["label"] in emotion_service.ALL_LABELS
    for k in res["scores"]:
        assert k in emotion_service.ALL_LABELS


def test_settings_do_not_return_secret(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert "openai_api_key" not in r.json()
    assert all(s["key"] != "openai_api_key" for s in r.json()["settings"])
