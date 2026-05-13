#!/usr/bin/env bash
# Linux deployment helper. Parent directory "prod" uses backend 8848;
# all other Linux paths use backend 9527.

set -e
export PATH="/usr/bin:${HOME}/.local/bin:/usr/local/bin:${PATH}"

CONDA_ENV="${CONDA_ENV:-Bender}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT="$(basename "$(dirname "$ROOT")")"

if [ "$PARENT" = "prod" ]; then
  PORT=8848
else
  PORT=9527
fi

echo "Parent dir: ${PARENT}; backend tcp port: ${PORT}"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found. Install example: npm install -g pnpm --prefix \"\$HOME/.local\"" >&2
  exit 1
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

echo "Building frontend..."
(cd "$ROOT/bbctg_vita_web" && pnpm -F @bbctg/antibody-vita run build)

echo "Freeing tcp:${PORT}..."
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -ti "tcp:${PORT}" 2>/dev/null || true)"
  [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
elif command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
fi

mkdir -p "$ROOT/repository/logs"
LOG="$ROOT/repository/logs/backend.nohup.log"

echo "Starting backend with nohup. Log: ${LOG}"
nohup bash -c "
source \"\$(conda info --base)/etc/profile.d/conda.sh\"
conda activate \"${CONDA_ENV}\"
cd \"${ROOT}/bbctg_vita_server\"
exec python server.py
" >>"$LOG" 2>&1 &

echo "Backend PID: $!"
