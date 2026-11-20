#!/usr/bin/env bash
# Start only the backend (which also serves the frontend on the same origin).
set -e
cd "$(dirname "$0")/../backend"
exec bash run.sh
