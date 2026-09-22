#!/usr/bin/env bash
# Migrate first, then supervise API, durable worker, and web. Ctrl-C stops all three.
set -euo pipefail
cd "$(dirname "$0")"
command -v uv >/dev/null || { echo "Install uv: https://docs.astral.sh/uv/" >&2; exit 1; }
command -v npm >/dev/null || { echo "Node.js 22+ is required." >&2; exit 1; }
if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; fi
if [ ! -d frontend/node_modules ]; then (cd frontend && npm ci); fi
(cd backend && uv sync --locked && uv run alembic upgrade head)
pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
(cd backend && exec uv run uvicorn app.main:app --reload --host 127.0.0.1 --port "${API_PORT:-8000}") &
pids+=("$!")
(cd backend && exec uv run python -m app.worker) &
pids+=("$!")
# Launch Next directly so shutdown reaches its signal handler instead of stopping only npm.
(cd frontend && exec node node_modules/next/dist/bin/next dev --port "${WEB_PORT:-3000}") &
pids+=("$!")
# Portable on macOS's Bash 3.2; exit if any child dies instead of leaving a half-running stack.
while true; do
  for pid in "${pids[@]}"; do if ! kill -0 "$pid" 2>/dev/null; then exit 1; fi; done
  sleep 2
done
