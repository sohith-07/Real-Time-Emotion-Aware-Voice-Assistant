#!/usr/bin/env bash
# Start the FastAPI backend (also serves the frontend at /).
set -e
cd "$(dirname "$0")"

# Create a virtualenv on first run if missing.
if [ ! -d ".venv" ]; then
  echo "Creating virtualenv (.venv)..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Install dependencies on first run or if requirements changed.
if ! python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
  echo "Installing dependencies (this may take a few minutes on first run)..."
  pip install --upgrade pip
  pip install -r requirements.txt || {
    echo "Full ML dependencies could not be installed; installing minimal dependencies."
    pip install -r requirements-minimal.txt
  }
fi

# Copy .env.example -> .env on first run.
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Starting EmotiVoice backend on http://localhost:8000"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
