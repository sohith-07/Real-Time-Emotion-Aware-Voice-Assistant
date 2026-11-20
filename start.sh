#!/usr/bin/env bash
# Top-level launcher: starts the FastAPI backend, which also serves
# the frontend at http://localhost:8000
set -e
cd "$(dirname "$0")/backend"
exec bash run.sh
