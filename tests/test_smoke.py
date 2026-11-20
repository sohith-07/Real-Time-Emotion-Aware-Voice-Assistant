"""Standalone smoke test - start the server and hit endpoints live.

Usage:
    python tests/test_smoke.py
or, after installing deps:
    python tests/test_smoke.py --base http://localhost:8000

Exits 0 on success, 1 on failure. Prints a summary.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def req(base: str, method: str, path: str, body=None):
    url = base + path
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    if body:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode(errors="replace")
            try:
                return resp.status, json.loads(raw or "{}")
            except json.JSONDecodeError:
                # Non-JSON response (e.g. HTML for "/") - return the raw text.
                return resp.status, {"_raw": raw[:200]}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    checks = []
    def check(name, cond, detail=""):
        checks.append((name, bool(cond), detail))
        mark = "PASS" if cond else "FAIL"
        print(f"[{mark}] {name}" + (f" - {detail}" if detail else ""))

    # Health
    s, b = req(base, "GET", "/api/health")
    check("health endpoint", s == 200 and b.get("status") == "ok", str(b)[:80])

    # Emotion labels
    s, b = req(base, "GET", "/api/emotion/labels")
    labels = b.get("labels", []) if s == 200 else []
    check("emotion labels (7)", len(labels) == 7, ",".join(labels))

    # Emotion detect
    s, b = req(base, "POST", "/api/emotion", {"text": "I am so happy today!"})
    check("emotion detect happy", s == 200 and b.get("label") in labels, str(b)[:80])

    # Chat
    s, b = req(base, "POST", "/api/chat", {"text": "Hello!", "mode": "text"})
    check("chat creates reply", s == 200 and b.get("reply"), b.get("reply", "")[:80])
    cid = b.get("conversation_id")

    # Conversation list
    s, b = req(base, "GET", "/api/conversations")
    check("conversations list", s == 200 and isinstance(b.get("conversations"), list), "")

    # Analytics
    s, b = req(base, "GET", "/api/analytics")
    check("analytics", s == 200 and "total_conversations" in b, str(b)[:80])

    # Settings
    s, b = req(base, "GET", "/api/settings")
    check("settings list", s == 200 and isinstance(b.get("settings"), list), "")

    # Voice info
    s, b = req(base, "GET", "/api/voice/info")
    check("voice info", s == 200 and b.get("tts_engine") == "web_speech_api", "")

    # Frontend served
    s, b = req(base, "GET", "/")
    check("frontend served", s in (200, 307), str(s))

    n_pass = sum(1 for _, ok, _ in checks if ok)
    n_fail = len(checks) - n_pass
    print(f"\n{n_pass}/{len(checks)} passed, {n_fail} failed.")
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
