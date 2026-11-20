#!/usr/bin/env bash
# Run all tests: offline pytest suite + (optional) live smoke test.
set -e
cd "$(dirname "$0")/../backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements-minimal.txt pytest 2>/dev/null || \
  pip install -q -r requirements.txt pytest

echo "=== Offline pytest suite ==="
python -m pytest ../tests/ -v

if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null | grep -q 200; then
  echo "=== Live smoke test (server detected on :8000) ==="
  python ../tests/test_smoke.py
else
  echo "(Skipped live smoke test - backend not running on :8000.)"
fi
