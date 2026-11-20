#!/usr/bin/env bash
# (Optional) Serve only the frontend separately on port 3000.
# Normally you do NOT need this - the backend serves the frontend on :8000.
# Use this only for frontend-only development; the API must be reachable at
# the same origin or via the ?api= query parameter.
set -e
cd "$(dirname "$0")/../frontend"
PORT="${1:-3000}"
echo "Serving frontend on http://localhost:$PORT"
echo "(Point API calls at the backend with ?api=http://localhost:8000 in the URL)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m http.server "$PORT"
else
  echo "python3 not found."
  exit 1
fi
