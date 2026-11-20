# API Reference

Base URL: `http://localhost:8000`

All endpoints are JSON. Interactive docs are auto-generated at `/docs` (Swagger UI) and `/redoc` once the server is running.

---

## Health

### `GET /api/health`
Returns service status and active engines.

**Response**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "app_name": "Emotion-Aware Voice Assistant",
  "emotion_engine": "transformers",
  "chat_engine": "rule",
  "openai_configured": false,
  "frontend_dir_exists": true
}
```

---

## Chat

### `POST /api/chat`
Send a user message and receive an emotion-aware assistant reply.

**Request body**
```json
{
  "text": "I'm feeling really great today!",
  "conversation_id": "abc123...",   // optional; omit to start a new conversation
  "mode": "voice"                    // "voice" | "text" (default "text")
}
```

**Response** — `200 OK`
```json
{
  "conversation_id": "abc123...",
  "user_message_id": "u1...",
  "assistant_message_id": "a1...",
  "reply": "That's wonderful to hear — your excitement really comes through! ...",
  "emotion": "happy",
  "emotion_confidence": 0.92,
  "emotion_scores": { "happy": 0.92, "sad": 0.01, "angry": 0.01, "fear": 0.02, "surprise": 0.02, "neutral": 0.01, "disgust": 0.01 },
  "engine": "rule",
  "note": "Emotion predictions are estimates and not psychological assessments."
}
```

**Errors**
- `422` — empty `text` or invalid `mode`.
- `500` — internal error (message in `detail`).

### `GET /api/chat/engines`
Returns which emotion and chat engines are active.

---

## Emotion

### `POST /api/emotion`
Detect emotion from a piece of text without sending a chat reply.

**Request**
```json
{ "text": "I am so happy today!" }
```

**Response** — `200 OK`
```json
{
  "label": "happy",
  "confidence": 0.92,
  "scores": { "happy": 0.92, "sad": 0.01, "angry": 0.01, "fear": 0.02, "surprise": 0.02, "neutral": 0.01, "disgust": 0.01 },
  "note": "Emotion predictions are estimates produced by an ML model ..."
}
```

### `GET /api/emotion/labels`
Returns the supported canonical emotion labels and the active engine.

---

## Conversations

### `GET /api/conversations?limit=50&offset=0`
List conversations, newest first.

### `GET /api/conversations/{id}`
Get a single conversation **with all its messages**.

### `GET /api/conversations/{id}/messages`
List the messages of a conversation in chronological order.

### `DELETE /api/conversations/{id}`
Delete a conversation and all of its messages (cascade).

### `POST /api/conversations/clear`
Delete **all** conversations. Body: none.

---

## Analytics

### `GET /api/analytics`
Returns aggregate stats for the dashboard.

**Response**
```json
{
  "total_conversations": 12,
  "total_messages": 47,
  "total_user_messages": 23,
  "total_assistant_messages": 24,
  "most_frequent_emotion": "happy",
  "emotion_distribution": [
    { "label": "happy", "count": 9, "percentage": 39.13 },
    { "label": "neutral", "count": 6, "percentage": 26.09 },
    ...
  ],
  "recent_messages": [
    { "id": "...", "conversation_id": "...", "role": "user", "content": "...", "emotion": "happy", "created_at": "2026-11-20T..." },
    ...
  ],
  "daily_counts": [
    { "date": "2026-11-19", "count": 12 },
    { "date": "2026-11-20", "count": 35 }
  ]
}
```

> Emotion counts are computed over **user messages only** (assistant messages are always tagged `neutral`).

---

## Settings

### `GET /api/settings`
Returns all settings, merging defaults with stored overrides.
```json
{
  "settings": [ { "key": "auto_play_tts", "value": "true" }, ... ],
  "defaults": { "auto_play_tts": "true", "voice_name": "", ... }
}
```

### `PUT /api/settings/{key}`
Update one setting.
```json
// PUT /api/settings/theme
{ "key": "theme", "value": "light" }
```
Special case: when `key == "openai_api_key"` and a non-empty value is supplied, the value is also written to `backend/.env` and set in the running process so the LLM service can use it immediately.

### `POST /api/settings`
Bulk update.
```json
{ "settings": [ { "key": "auto_play_tts", "value": "false" }, { "key": "theme", "value": "light" } ] }
```

### `POST /api/settings/reset`
Delete all stored settings; defaults are reseeded.

### `GET /api/settings/{key}`
Get a single setting.

---

## Voice

### `GET /api/voice/info`
Returns Web Speech API capabilities and per-emotion voice hints (rate/pitch suggestions the frontend can apply).

### `GET /api/voice/voices`
Stub. Real voices are discovered at runtime in the browser via `speechSynthesis.getVoices()`.

### `GET /api/voice/tts?text=...&lang=en`
**Optional** server-side TTS using `gTTS`. Returns an `audio/mpeg` stream. Only useful if the browser has no `SpeechSynthesis`. Requires `pip install gTTS` and an internet connection. Returns `503` if `gTTS` is not installed.

---

## Static frontend

| Route | Serves |
| --- | --- |
| `GET /` | Redirects to `/index.html` |
| `GET /index.html`, `/voice.html`, `/chat.html`, `/analytics.html`, `/settings.html` | The HTML pages |
| `GET /voice`, `/chat`, `/analytics`, `/settings` | Same pages via bare routes |
| `GET /static/css/style.css`, `/static/js/*.js` | Static assets |

---

## Example session with `curl`

```bash
# Health
curl -s http://localhost:8000/api/health | jq

# Detect emotion
curl -s -X POST http://localhost:8000/api/emotion \
  -H 'Content-Type: application/json' \
  -d '{"text": "I am so happy today!"}' | jq

# Chat
curl -s -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"text": "I feel really sad and lonely", "mode": "voice"}' | jq

# Analytics
curl -s http://localhost:8000/api/analytics | jq
```
