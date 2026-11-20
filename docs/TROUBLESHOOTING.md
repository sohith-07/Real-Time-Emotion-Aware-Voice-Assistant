# Troubleshooting

## 1. The microphone doesn't respond / "Speech recognition not supported"

**Cause**: your browser doesn't support the Web Speech API `SpeechRecognition`. Most common with Firefox.

**Fix**:
- Use **Google Chrome** or **Microsoft Edge** (Chromium-based). Safari 14+ mostly works on macOS.
- Make sure you're serving over `http://localhost` or `https://`. Some browsers block `SpeechRecognition` on `file://` or remote HTTP origins.
- On Chrome, check **site permissions**: click the lock/info icon next to the URL → Site settings → Microphone → Allow.

**Workaround**: use the **Text Chat** page instead, which doesn't need the mic.

---

## 2. The mic button blinks red but nothing is transcribed

- Check your OS microphone is not muted and the correct input device is selected.
- Speak closer to the mic, in a quieter room.
- Try setting a different recognition language in **Settings → Recognition language** that matches how you speak.
- On Linux, you may need to grant the browser mic access: `pulseaudio`/`pipewire` should be running; if you use Chromium via Snap/Flatpak, confirm it has the `audio-record` permission.

---

## 3. The assistant doesn't speak replies

- Confirm **Auto-play** is ticked on the Voice page.
- Confirm **Settings → Speech & Voice → Speech rate/pitch** are within sane range (0.5–2.0).
- Some browsers (`Chrome` on Linux without `speech-dispatcher`) have no system TTS voices. Check `speechSynthesis.getVoices()` length in the browser console. If empty, install `speech-dispatcher` and a voice (`espeak-ng`), or use the **🔊 Speak last** button on the Text Chat page after picking a voice in Settings.
- On mobile Safari, TTS must be triggered by a user gesture — clicking the mic or the speak button counts.

---

## 4. `pip install` fails on `torch`

The `torch` wheel is ~800 MB and may fail on slow or restricted networks.

**Fixes**:
- Use the minimal requirements file instead:
  ```bash
  cd backend
  pip install -r requirements-minimal.txt
  ```
  Emotion detection then uses the lexical fallback engine (same 7 labels).
- Or install a CPU-only torch wheel:
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  ```

---

## 5. First request is slow (10–30 s)

This is the HuggingFace model downloading weights (~135 MB) and warming up. Subsequent calls are < 200 ms. The model is cached in `~/.cache/huggingface/` for next time.

To skip the model entirely, set `EMOTION_FALLBACK_ENABLED=true` (default) and use `requirements-minimal.txt`.

---

## 6. `Port 8000 already in use`

```bash
# Find and kill the process holding the port
lsof -i :8000      # macOS/Linux
netstat -ano | findstr :8000   # Windows
```
Or start on a different port:
```bash
python -m uvicorn app.main:app --port 8080
```
Then open `http://localhost:8080`.

---

## 7. `ModuleNotFoundError: No module named 'app'`

You're running uvicorn from the wrong directory. Always run from inside `backend/`:
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 8. `ImportError: cannot import name 'BaseSettings' from 'pydantic_settings'`

You have an old `pydantic-settings`. Reinstall:
```bash
pip install --upgrade "pydantic-settings>=2.2.1"
```

---

## 9. The Settings page can't save the OpenAI key

- The key writes to `backend/.env`. Make sure the backend process has write permission on that file.
- After saving, the running process picks up the key immediately; you don't need to restart.
- Verify with `curl http://localhost:8000/api/health` → `"openai_configured": true`.

If OpenAI calls still fail, check the server logs for the actual error (rate limit, invalid key, network). The assistant will silently fall back to the rule engine.

---

## 10. Analytics charts are blank

- Charts use Chart.js loaded from a CDN (`cdn.jsdelivr.net`). If you're offline, the canvas is skipped — but the KPI numbers and lists still render.
- If you have at least one conversation but KPIs are zero, refresh the page or click **↻ Refresh**.
- Verify the backend has data: `curl http://localhost:8000/api/analytics`.

---

## 11. Database locked / `sqlite3.OperationalError`

Happens if two server processes share `assistant.db`. Make sure only one `uvicorn` is running. The default config uses `check_same_thread=False` and a single connection pool, which is safe for one process.

If the DB is corrupted, delete `backend/assistant.db` and restart — it's recreated automatically with defaults.

---

## 12. CORS errors in the browser console

If you serve the frontend from a different origin than the API (e.g. `python -m http.server 3000` for the frontend and uvicorn on 8000), add the frontend origin to `CORS_ORIGINS` in `backend/.env`:
```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
Restart the server. By default the backend serves the frontend itself on the same origin, so CORS is not needed.

---

## 13. Theme doesn't persist

- The theme is saved both in `localStorage` and in the backend `app_settings` table.
- If you clear browser storage, the backend setting is used as a fallback on next load.
- Hard-refresh (Ctrl+Shift+R) if a page seems stuck on the wrong theme.

---

## 14. Where are the logs?

The server logs to stdout. To see them, run uvicorn in the foreground (the default). For verbose logs, set `LOG_LEVEL=DEBUG` in `backend/.env`.

---

## 15. Still stuck?

1. Run the smoke test: `python tests/test_smoke.py` — it tells you exactly which endpoint is broken.
2. Run the offline tests: `cd backend && pytest ../tests/ -v`.
3. Check `/api/health` and `/docs` (Swagger UI) to confirm the backend is alive.
4. Open the browser DevTools Console (F12) for frontend errors.
