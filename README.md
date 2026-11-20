# EmotiVoice — Real-Time Voice Assistant with Emotion-Aware Dialogue

A complete, working voice assistant that **listens** to you, **detects your emotion** from what you say, **adapts its replies** to your mood, and **speaks the response** out loud — all in real time, running on a normal laptop.

> **Emotion predictions are estimates produced by an ML model and are *not* definitive psychological assessments.** They are used only to adapt the assistant's conversational tone.

---

## ✨ Features

| Area | What you get |
| --- | --- |
| **Real-time voice** | Click-to-talk microphone, live transcript, sound-wave visualizer, stop / interrupt controls |
| **Speech recognition (ASR)** | Browser Web Speech API — no API key, no install |
| **Emotion detection** | HuggingFace `j-hartmann/emotion-english-distilroberta-base` model → 7 emotions (joy, sadness, anger, fear, surprise, disgust, neutral) with confidence + full probability distribution. Automatic lexical fallback if the model can't load |
| **Emotion-aware dialogue** | Rule engine that adapts tone to emotion, tracks context, avoids repetition; optional OpenAI integration via env var |
| **Text-to-speech (TTS)** | Browser SpeechSynthesis, voice selection, rate / pitch sliders, autoplay toggle |
| **Text chat mode** | Separate page with conversation list, bubbles, emotion badges, clear-chat |
| **Analytics dashboard** | KPIs, emotion-distribution doughnut, daily-volume bar chart, recent activity, breakdown |
| **Settings** | Microphone, voice, speech rate/pitch, emotion detection, theme (dark/light), optional OpenAI key |
| **Persistence** | SQLite database auto-created on first run |
| **Premium UI** | Modern dark/light theme, responsive, animations, glass-morphism — demo-grade |

---

## 🧱 Tech Stack

**Backend** — Python 3.9+, FastAPI, SQLAlchemy 2, Pydantic 2, SQLite, HuggingFace Transformers + Torch (optional), OpenAI SDK (optional).

**Frontend** — Vanilla HTML5, CSS3, ES6 JavaScript. No build step, no npm install. Uses the **Web Speech API** (`SpeechRecognition` + `SpeechSynthesis`) built into Chrome / Edge / Safari.

**Why this stack?**
- Runs on any laptop with Python 3.9+ and a modern browser.
- Zero external API keys required — fully functional out of the box.
- Real ML emotion model (DistilRoBERTa fine-tuned on emotion datasets).
- One server, one command to start.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+** (check with `python3 --version`)
- A modern browser: **Chrome** or **Edge** recommended (best Web Speech API support). Safari mostly works. Firefox has limited `SpeechRecognition`.
- A working microphone.

### Run

**Linux / macOS**
```bash
cd /path/to/Real-Time-Emotion-Aware-Voice-Assistant
bash start.sh
```

Open **http://localhost:8000**. The project creates `backend/.venv` and `backend/assistant.db` automatically.

For a manual setup:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-minimal.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Windows (PowerShell)**
```powershell
cd Real-Time-Emotion-Aware-Voice-Assistant\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in Chrome or Edge.

> The first run installs Python dependencies (torch + transformers can take a few minutes the first time). On a slow machine or restricted network, use `pip install -r backend/requirements-minimal.txt` instead — emotion detection then uses the built-in lexical fallback engine (same 7 labels, slightly less accurate).

---

## ⚙️ Optional: Enable OpenAI Chat (richer replies)

The app works fully without it. To use GPT replies instead of the rule engine:

1. Edit `backend/.env`:
   ```env
   CHAT_ENGINE=openai
   OPENAI_API_KEY=sk-...your-key...
   OPENAI_MODEL=gpt-3.5-turbo
   ```
2. Restart the server. (Or set the key from the **Settings** page — it writes to `.env` automatically.)

If the key is missing or the call fails, the assistant automatically falls back to the emotion-aware rule engine.

---

## 🗂️ Project Structure

```
Real-Time-Emotion-Aware-Voice-Assistant/
├── start.sh                      # Top-level launcher
├── README.md                     # This file
├── backend/
│   ├── run.sh                    # Backend launcher (venv + deps + uvicorn)
│   ├── requirements.txt          # Full deps (with torch + transformers)
│   ├── requirements-minimal.txt  # Light deps (lexical fallback)
│   ├── .env.example              # Copy to .env
│   └── app/
│       ├── main.py               # FastAPI app + static mount + startup
│       ├── config.py             # Settings (env-driven)
│       ├── database.py           # Engine, session, init_db()
│       ├── models.py             # Conversation, Message, AppSetting ORM
│       ├── schemas.py            # Pydantic request/response models
│       ├── routers/              # chat, emotion, conversations,
│       │                         # analytics, settings, voice
│       └── services/
│           ├── emotion_service.py     # HF model + lexical fallback
│           ├── llm_service.py          # Rule engine + OpenAI
│           └── conversation_service.py # Orchestration
├── frontend/
│   ├── index.html                # Landing
│   ├── voice.html                # Voice assistant
│   ├── chat.html                 # Text chat
│   ├── analytics.html            # Dashboard
│   ├── settings.html             # Settings
│   ├── css/style.css             # Shared premium theme
│   └── js/                       # common, voice, chat, analytics, settings
├── docs/
│   ├── INSTALLATION.md
│   ├── USER_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── TROUBLESHOOTING.md
│   └── PROJECT_REPORT.md         # Full 19-section academic report
└── tests/
    ├── test_backend.py           # Pytest suite
    └── test_smoke.py             # Live HTTP smoke test
```

---

## 🧪 Tests

```bash
cd backend
pip install -r requirements.txt pytest
pytest ../tests/ -v                # unit + endpoint tests (offline-safe)

# Live smoke test (start the server first, then in another terminal):
python ../tests/test_smoke.py
```

See **docs/PROJECT_REPORT.md §14 Testing** for the full verification matrix.

---

## 📖 Documentation

- [Installation guide](docs/INSTALLATION.md)
- [User guide](docs/USER_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Full project report](docs/PROJECT_REPORT.md) — abstract, problem statement, architecture, algorithms, model descriptions, testing, results, limitations, future work, references.

---

## ⚠️ Known Limitations

- **Web Speech API browser support**: `SpeechRecognition` works best in Chrome / Edge. Firefox support is limited. If unavailable, the Voice page shows a warning; the Text Chat page still works fully.
- **Emotion model is text-based**: the model analyses the *transcribed text*, not raw audio prosody. Heavily sarcastic or deadpan speech may be classified as neutral.
- **First HuggingFace model load** downloads ~500 MB of weights on first run and takes 10–30 s; subsequent runs are cached. Use `requirements-minimal.txt` to skip this entirely.
- **OpenAI integration is optional**: without a key, the rule engine is used. It is genuinely context-aware but not as fluent as GPT.
- **No user authentication**: the app is designed for local single-user demonstration, not multi-tenant deployment.

---

## 📜 License

MIT — see `LICENSE` (educational / demo project).
