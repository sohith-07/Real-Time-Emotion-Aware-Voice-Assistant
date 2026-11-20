# User Guide

This guide walks you through every screen of EmotiVoice.

> **Emotion predictions are estimates produced by an ML model and are *not* psychological assessments.** They are intended only to adapt the assistant's conversational tone.

---

## 1. Home (`/`)

The landing page introduces the project and links to the four main areas:
- **Voice Assistant** — speak to the AI
- **Text Chat** — type to the AI
- **Analytics** — view stats
- **Settings** — configure the app

Use the **sun/moon button** (top-right) to toggle dark / light theme.

---

## 2. Voice Assistant (`/voice`)

This is the centrepiece. Layout: microphone panel on the left, live emotion + conversation transcript on the right.

### 2.1 Start a voice conversation
1. Click the round **🎙 microphone button** in the centre.
2. The button turns red and pulses, the **sound-wave bars** animate, and the status reads *"Listening… speak now."*
3. Speak a sentence (e.g. *"I'm feeling really great today, I just got a new job!"*).
4. Your live transcription appears under the mic.
5. When you pause for ~1 second, recognition finalises and the assistant:
   - **Detects your emotion** from the transcribed text and shows it on the right.
   - **Generates an emotion-aware reply** and adds it to the transcript.
   - **Speaks the reply aloud** automatically (if Auto-play is on).
6. Click the mic again to send your next turn.

### 2.2 Controls
| Control | What it does |
| --- | --- |
| **Mic button** | Start / stop listening. Click while the assistant is speaking to interrupt. |
| **⏹ Stop speaking** | Cancel the current TTS playback. |
| **🗑 Clear** | Reset the current conversation and emotion panel. |
| **Auto-play toggle** | If on (default), every assistant reply is spoken aloud. Turn off to read replies silently. |

### 2.3 Live emotion panel
Shows the **current emotion badge** (e.g. `happy · 87%`) plus a horizontal bar chart of all 7 emotion probabilities for your last message.

---

## 3. Text Chat (`/chat`)

For when you can't (or don't want to) speak.

- **Left column**: list of past conversations. Click any to reopen. **+ New chat** starts a fresh one. **Clear all** wipes everything.
- **Main column**: chat bubbles. **Your messages** appear on the right (indigo, with an emotion badge). **Assistant replies** appear on the left (with a green "speaking" pill).
- **Input**: type at the bottom. **Enter** to send, **Shift+Enter** for a new line.
- **🔊 Speak last**: speak the most recent assistant reply out loud (toggle).

---

## 4. Analytics (`/analytics`)

- **Top KPIs**: total conversations, total messages, user/assistant message counts, most-frequent emotion.
- **Emotion distribution doughnut**: share of each emotion across all *user* messages.
- **Daily message volume**: bar chart of the last 14 days.
- **Recent messages**: the 20 most recent exchanges with emotion badges and timestamps.
- **Emotion breakdown**: ranked bar list.
- **↻ Refresh**: re-pull from the backend.

> Charts use Chart.js loaded from a CDN. If you're offline, the chart canvases are skipped but the KPIs and lists still render.

---

## 5. Settings (`/settings`)

Three cards:

### Voice Interaction
- **Automatic speech playback** — toggle TTS autoplay.
- **Microphone enabled** — allow voice input.
- **Interrupt while speaking** — let the mic button stop TTS mid-utterance.
- **Sound-wave visualizer** — show animated bars while listening.

### Speech & Voice
- **Voice** — pick any voice installed in your OS (populated from `speechSynthesis.getVoices()`).
- **Speech rate** — 0.5× – 2× (default 1.0).
- **Speech pitch** — 0.5 – 2.0.
- **Recognition language** — affects both ASR and TTS locale.
- **🔊 Test voice** — speak a sample sentence with current settings.

### Emotion, Theme & API
- **Emotion detection** — toggle per-message analysis.
- **Theme** — dark / light.
- **OpenAI API key** — paste a key to enable GPT replies (writes to `backend/.env` and activates immediately; leave empty to use the rule engine).

Click **Save settings** to persist all changes to the SQLite database, or **Reset to defaults** to restore factory values.

---

## 6. Tips for a great demo

1. **Use Chrome or Edge** — the Web Speech API is most reliable there.
2. **Allow microphone permission** when prompted.
3. **Speak naturally and emotively** — the emotion model is more accurate on expressive sentences ("I'm so happy!", "I feel awful today") than on terse ones.
4. **Try different emotions** in one session to watch the assistant's tone adapt.
5. **Open the Analytics page** after a few exchanges to show the charts filling in.

---

## 7. Privacy

- Conversations, messages and emotion predictions are stored **locally** in `backend/assistant.db` (SQLite). They never leave your machine.
- The OpenAI key, if you set one, is written to `backend/.env` on your machine and is sent only to OpenAI when the chat engine is `openai`.
- The HuggingFace emotion model runs **locally** after its first download; no text is sent to any cloud inference endpoint.
