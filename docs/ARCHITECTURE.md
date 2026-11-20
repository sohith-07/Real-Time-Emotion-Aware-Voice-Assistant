# Architecture

## 1. High-level view

```
 ┌────────────────────────────────────────────────────────────┐
 │                      Browser (Chrome/Edge)                  │
 │                                                              │
 │  HTML pages  ←→  common.js (API client, theme, sidebar)     │
 │       │                │                                    │
 │       │                │  fetch JSON over HTTP              │
 │       │                ▼                                    │
 │  Web Speech API:        ┌───────────────────────────────┐  │
 │   SpeechRecognition     │   FastAPI backend (Python)     │  │
 │   SpeechSynthesis       │   http://localhost:8000        │  │
 │                        │                                 │  │
 │                        │   routers/                      │  │
 │                        │    chat  emotion  conversations │  │
 │                        │    analytics  settings  voice   │  │
 │                        │         │                       │  │
 │                        │         ▼                       │  │
 │                        │   services/                     │  │
 │                        │    emotion_service (HF + lex)   │  │
 │                        │    llm_service (rule + OpenAI)  │  │
 │                        │    conversation_service         │  │
 │                        │         │                       │  │
 │                        │         ▼                       │  │
 │                        │   SQLAlchemy ORM                │  │
 │                        │         │                       │  │
 │                        │   SQLite (assistant.db)         │  │
 │                        └───────────────────────────────┘  │
 └────────────────────────────────────────────────────────────┘
```

The backend serves the frontend as static files (`/static/*`) on the **same origin** as the API, so there are no CORS issues during normal use. CORS is still enabled for development when the frontend is served from another port.

---

## 2. Request flow — one voice turn

1. User clicks the mic button → `SpeechRecognition.start()`.
2. Browser streams audio to its own ASR engine and returns text via `onresult`.
3. Frontend posts `POST /api/chat { text, conversation_id?, mode: "voice" }`.
4. `routers/chat.py` calls `conversation_service.handle_user_message()`:
   1. Looks up or creates a `Conversation` row.
   2. Inserts the `Message(role="user", content=text)`.
   3. Calls `emotion_service.detect(text)` → returns label + confidence + scores.
   4. Stores the emotion on the user message.
   5. Builds the prior-message history (last 10 turns) for context.
   6. Calls `llm_service.generate_reply(text, emotion, history)` → `(reply, engine)`.
   7. Inserts the assistant `Message`.
   8. Returns the assembled JSON.
5. Frontend renders the user bubble (with emotion badge), the assistant bubble, and the live emotion bars.
6. If **Auto-play** is on, the frontend creates a `SpeechSynthesisUtterance(reply)` and calls `speechSynthesis.speak()`.

Total round-trip on a laptop with the model cached: typically 200–600 ms for the API call (most of which is the HF inference), plus TTS latency from the browser.

---

## 3. Component breakdown

### 3.1 Backend (`backend/app/`)

| Module | Responsibility |
| --- | --- |
| `main.py` | FastAPI app instance, CORS, startup (`init_db`, `seed_defaults`), router registration, static mount, `/api/health`, `/` redirect. |
| `config.py` | Pydantic `Settings` loaded from `.env`. Exposes `use_openai` resolver. |
| `database.py` | SQLAlchemy engine (SQLite with FK enforcement), `SessionLocal`, `init_db()`, `get_db()` dependency, `db_session()` context manager. |
| `models.py` | ORM models: `Conversation`, `Message`, `AppSetting`; default-setting seeding helpers. |
| `schemas.py` | Pydantic v2 request/response models for every endpoint. |
| `routers/chat.py` | `POST /api/chat`, `GET /api/chat/engines`. |
| `routers/emotion.py` | `POST /api/emotion`, `GET /api/emotion/labels`. |
| `routers/conversations.py` | CRUD: list / get / delete / clear / messages. |
| `routers/analytics.py` | Aggregate stats for the dashboard. |
| `routers/settings.py` | Key/value settings; special handling writes `OPENAI_API_KEY` to `.env`. |
| `routers/voice.py` | Voice capability metadata + optional server-side gTTS fallback. |
| `services/emotion_service.py` | HuggingFace `pipeline` (lazy-loaded) + lexical fallback → canonical 7-label scores. |
| `services/llm_service.py` | Emotion-aware rule engine + optional OpenAI Chat Completions. |
| `services/conversation_service.py` | Orchestrates emotion + LLM + persistence in one call. |

### 3.2 Frontend (`frontend/`)

| File | Responsibility |
| --- | --- |
| `index.html` | Landing page with hero + feature grid. |
| `voice.html` + `js/voice.js` | Mic button, wave visualizer, live transcript, TTS, emotion bars. |
| `chat.html` + `js/chat.js` | Conversation list, bubbles, text input. |
| `analytics.html` + `js/analytics.js` | KPIs + Chart.js doughnut/bar + recent activity. |
| `settings.html` + `js/settings.js` | All settings forms, voice picker, OpenAI key field. |
| `css/style.css` | Shared premium dark/light theme + components. |
| `js/common.js` | API client, sidebar shell, theme, toasts, helpers. |

---

## 4. Emotion detection design

Two engines, both producing the **same 7 canonical labels**:

1. **Primary — HuggingFace transformers**
   - Model: `j-hartmann/emotion-english-distilroberta-base` (DistilRoBERTa fine-tuned on a 6-emotion English dataset, plus `neutral`).
   - Loaded lazily on first call via `pipeline("text-classification", top_k=None)`.
   - Returns all label probabilities, which we map to canonical labels and renormalise.

2. **Fallback — lexical scoring**
   - Per-emotion lexicons with weights; intensifier boosting ("very", "extremely"…).
   - Phrase matching via 1-, 2-, and 3-gram windows.
   - Softmax-style normalisation to a probability distribution.

Selection: if `EMOTION_FALLBACK_ENABLED=true` (default), the transformers engine is tried first; if it returns nothing (library missing, model not downloadable, inference error), the lexical engine is used. The active engine is reported by `GET /api/health` and on the Settings page.

---

## 5. Dialogue engine design

The rule engine (`llm_service._compose_reply`) is genuinely adaptive, not a fixed lookup:

1. **Acknowledgement** chosen from the emotion's tone pool (`_TONE_ACK`), avoiding the last 3 used to prevent verbatim repeats.
2. **Intent body** matched from keyword patterns (`_INTENTS`) — greetings, help, jokes, work, study, stress, relationships, yes/no, etc. — again with anti-repeat filtering.
3. **Question handling** — if the user asked a question and no intent matched, a reflective, two-angle reply is generated.
4. **Follow-up** — a rotating follow-up question is appended ~50% of the time to keep the exchange flowing.

OpenAI integration, when enabled, wraps the same emotion into a system prompt that instructs the model to adapt tone per emotion, and sends the last 10 turns for context. On any failure (missing key, network, rate limit) it silently falls back to the rule engine.

---

## 6. Database schema

```
conversations
  id          TEXT PK
  title       TEXT
  mode        TEXT  (voice | text)
  created_at  TIMESTAMP
  updated_at  TIMESTAMP

messages
  id                 TEXT PK
  conversation_id    TEXT FK -> conversations.id (CASCADE)
  role               TEXT (user | assistant)
  content            TEXT
  emotion            TEXT (canonical label, nullable)
  emotion_confidence REAL
  emotion_scores     TEXT (JSON)
  audio_url          TEXT
  created_at         TIMESTAMP

app_settings
  key         TEXT PK
  value       TEXT
  updated_at  TIMESTAMP
```

SQLite is used because it requires no separate server, is file-based, and is more than fast enough for a single-user local assistant. The schema is portable to PostgreSQL/MySQL by changing `DATABASE_URL` (FK and cascade semantics are standard SQL).

---

## 7. Real-time strategy

- **ASR**: the browser's `SpeechRecognition` runs locally in real time and streams interim transcripts; the backend only sees the final text.
- **Inference**: the HF model is small (~135 M params) and inference is < 100 ms per call on CPU once loaded.
- **TTS**: `speechSynthesis.speak()` is non-blocking and starts as soon as the reply arrives.
- **No WebSocket needed**: each turn is a single HTTP round-trip of a few hundred bytes; latency is dominated by model inference, not transport.

---

## 8. Security considerations

- No user authentication — designed for local single-user use. Do not expose the server to the public internet without adding auth.
- The OpenAI key, if set via the UI, is written to `backend/.env` on disk. Add `.env` to `.gitignore` (already done).
- CORS is restricted to localhost origins by default.
- No third-party telemetry. The HuggingFace model runs locally after first download.
