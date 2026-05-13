#!/usr/bin/env bash
set -e

CONDA_ENV=Bender
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v lsof >/dev/null 2>&1; then
  PIDS="$({ lsof -ti tcp:8888 2>/dev/null || true; lsof -ti tcp:5777 2>/dev/null || true; } | sort -u)"
  [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
else
  pkill -f "python.*server.py" 2>/dev/null || true
  pkill -f "pnpm.*@bbctg/antibody-vita.*dev" 2>/dev/null || true
fi

source "$(conda info --base)/etc/profile.d/conda.sh"

(cd "$ROOT/bbctg_vita_server" && conda activate "$CONDA_ENV" && python server.py) &
sleep 1
(cd "$ROOT/bbctg_vita_web" && pnpm -F @bbctg/antibody-vita run dev) &

wait
