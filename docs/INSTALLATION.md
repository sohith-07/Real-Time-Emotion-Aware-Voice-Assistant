# Installation Guide

## 1. System Requirements

### Hardware
| Component | Minimum | Recommended |
| --- | --- | --- |
| CPU | Dual-core x86_64 | Quad-core or better |
| RAM | 4 GB | 8 GB |
| Disk | 1.5 GB (incl. model cache) | 3 GB |
| Microphone | Any | USB or headset mic |
| Speakers / headphones | Any | Yes |
| Internet | Required for first run (model download) | Not required afterwards |

### Software
| Component | Version |
| --- | --- |
| OS | Windows 10+, macOS 11+, or Linux (Ubuntu 20.04+ tested) |
| Python | **3.9 – 3.11** (3.10 recommended) |
| Browser | Chrome 90+ or Edge 90+ (best Web Speech API support). Safari 14+ mostly works. Firefox: limited. |
| Git | Optional, only if cloning |

---

## 2. Step-by-step Installation

### 2.1 Get the project

If you received the ZIP:
```bash
unzip Real-Time-Emotion-Aware-Voice-Assistant.zip
cd Real-Time-Emotion-Aware-Voice-Assistant
```

### 2.2 Verify Python

```bash
python3 --version
# Should print 3.9.x – 3.11.x
```

If you don't have Python, install it from <https://www.python.org/downloads/>.

### 2.3 (Recommended) Use the bundled launcher

**Linux / macOS**
```bash
bash start.sh
```
The launcher will:
1. Create a virtualenv in `backend/.venv` (first run only).
2. Install dependencies from `backend/requirements.txt` (first run only — can take 3–8 min the first time because of `torch`).
3. Copy `.env.example` → `.env` if `.env` is missing.
4. Start `uvicorn` on `http://0.0.0.0:8000`.

**Windows**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2.4 Open the app

Visit **http://localhost:8000** in Chrome or Edge.

The browser will ask for microphone permission the first time you click the mic button on the Voice page — click **Allow**.

---

## 3. Minimal install (no torch / no model download)

If `torch` + `transformers` are too heavy or your network blocks the model download:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\Activate
pip install -r requirements-minimal.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The emotion engine then uses the built-in **lexical fallback** (same 7 labels: joy, sadness, anger, fear, surprise, disgust, neutral). The Health endpoint and Settings page will report `emotion_engine = fallback`.

---

## 4. Optional: enable OpenAI chat

Edit `backend/.env`:
```env
CHAT_ENGINE=openai
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-3.5-turbo
```
Restart the server. Or set the key from the **Settings** page in the UI (it writes to `.env` and reloads automatically).

If the key is missing or the OpenAI call fails, the assistant automatically falls back to the rule engine.

---

## 5. Verify the install

Open another terminal:
```bash
curl http://localhost:8000/api/health
# {"status":"ok","version":"1.0.0","emotion_engine":"...","chat_engine":"..."}

python tests/test_smoke.py
# Runs ~9 live HTTP checks against the running server.
```

Or run the offline pytest suite:
```bash
cd backend
pip install pytest
pytest ../tests/ -v
```

---

## 6. Uninstall

Just delete the project folder. The only external artefacts are:
- `backend/.venv/` (inside the project)
- `backend/assistant.db` (SQLite file, inside the project)
- The HuggingFace model cache at `~/.cache/huggingface/` (delete to reclaim ~500 MB).

No system-wide changes were made.
