#!/usr/bin/env bash
# Linux deployment helper: ./start_dev.sh [restart|stop|status|ensure|cron]; no argument means restart.
# Parent directory "prod" uses backend 8848 / pet-proxy 18765; all other Linux paths use 9527 / 18766.
# restart also keeps the cron entries (watchdog every minute, backup.sh at 03:30) in place.

set -e
export PATH="/usr/bin:/bin:${HOME}/.local/bin:/usr/local/bin:${PATH}"

CONDA_ENV="${CONDA_ENV:-Bender}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT="$(basename "$(dirname "$ROOT")")"

if [ "$PARENT" = "prod" ]; then
  PORT=8848
  PET_PORT=18765
else
  PORT=9527
  PET_PORT=18766
fi

LOG="$ROOT/repository/logs/backend.nohup.log"
PET_LOG="$ROOT/repository/logs/pet-proxy.nohup.log"
RUN_DIR="$ROOT/repository/run"
STOP_MARK="$RUN_DIR/backend.stopped"
ENSURE_MARK="$RUN_DIR/ensure.last"
PET_ENSURE_MARK="$RUN_DIR/ensure-pet.last"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
PET_HEALTH_URL="http://127.0.0.1:${PET_PORT}/api/pet/health"
CRON_TAG="# antibody-forge:${ROOT}"

ACTION="${1:-restart}"
case "$ACTION" in
  start) ACTION=restart ;;
  restart|stop|status|ensure|cron) ;;
  *)
    echo "Usage: $0 [restart|stop|status|ensure|cron]" >&2
    exit 2
    ;;
esac

mkdir -p "$RUN_DIR" "$ROOT/repository/logs"

# restart / stop / ensure must not interleave: the cron watchdog would restart a backend mid-deploy.
if [ "$ACTION" != "status" ] && [ "$ACTION" != "cron" ] && command -v flock >/dev/null 2>&1; then
  exec 9>"$RUN_DIR/start_dev.lock"
  if [ "$ACTION" = "ensure" ]; then
    flock -n 9 || exit 0
  else
    flock 9
  fi
fi

conda_base() {
  if command -v conda >/dev/null 2>&1; then
    conda info --base
    return
  fi
  for dir in "${CONDA_BASE:-}" "$HOME/anaconda3" "$HOME/miniconda3" /opt/conda /opt/anaconda3 /opt/miniconda3; do
    if [ -n "$dir" ] && [ -f "$dir/etc/profile.d/conda.sh" ]; then
      echo "$dir"
      return
    fi
  done
  echo "conda not found; set CONDA_BASE" >&2
  return 1
}

# Only the listening process: nginx upstream connections also use this port.
listen_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser "$1/tcp" 2>/dev/null || true
  fi
}

backend_pids() { listen_pids "$PORT"; }
pet_pids() { listen_pids "$PET_PORT"; }

stop_backend() {
  local pids
  pids="$(backend_pids)"
  if [ -z "$pids" ]; then
    echo "Backend not running on tcp:${PORT}"
    return 0
  fi
  echo "Stopping backend on tcp:${PORT} (PID $(echo $pids))..."
  kill $pids 2>/dev/null || true
  for _ in $(seq 1 10); do
    if [ -z "$(backend_pids)" ]; then
      echo "Backend stopped."
      return 0
    fi
    sleep 1
  done
  echo "Backend still running after 10s, killing."
  kill -9 $(backend_pids) 2>/dev/null || true
}

start_backend() {
  local base
  base="$(conda_base)"
  local drm_lib="${ROOT}/bbctg_vita_server/integrations/drm/lib"
  if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 52428800 ]; then
    mv -f "$LOG" "$LOG.1"
  fi
  echo "Starting backend with nohup. Log: ${LOG}"
  nohup bash -c "
source \"${base}/etc/profile.d/conda.sh\"
conda activate \"${CONDA_ENV}\"
export LD_LIBRARY_PATH=\"${drm_lib}:\${LD_LIBRARY_PATH:-}\"
cd \"${ROOT}/bbctg_vita_server\"
exec python server.py
" >>"$LOG" 2>&1 9>&- &
  BACKEND_PID=$!
  echo "Backend PID: ${BACKEND_PID}"
}

stop_pet() {
  local pids
  pids="$(pet_pids)"
  [ -z "$pids" ] && return 0
  echo "Stopping pet-proxy on tcp:${PET_PORT} (PID $(echo $pids))..."
  kill $pids 2>/dev/null || true
  for _ in $(seq 1 5); do
    [ -z "$(pet_pids)" ] && return 0
    sleep 1
  done
  kill -9 $(pet_pids) 2>/dev/null || true
}

start_pet() {
  [ -f "$ROOT/pet-proxy/server.py" ] || return 0
  local base
  base="$(conda_base)"
  if [ -f "$PET_LOG" ] && [ "$(stat -c %s "$PET_LOG")" -gt 52428800 ]; then
    mv -f "$PET_LOG" "$PET_LOG.1"
  fi
  echo "Starting pet-proxy on tcp:${PET_PORT}. Log: ${PET_LOG}"
  nohup bash -c "
source \"${base}/etc/profile.d/conda.sh\"
conda activate \"${CONDA_ENV}\"
cd \"${ROOT}/pet-proxy\"
export PET_PORT=\"${PET_PORT}\" PYTHONDONTWRITEBYTECODE=1
exec python server.py
" >>"$PET_LOG" 2>&1 9>&- &
}

# The pet is optional: a failed start is reported but does not fail the deployment.
wait_pet() {
  [ -f "$ROOT/pet-proxy/server.py" ] && command -v curl >/dev/null 2>&1 || return 0
  for _ in $(seq 1 10); do
    if curl -fsS "$PET_HEALTH_URL" >/dev/null 2>&1; then
      echo "Pet-proxy is up: ${PET_HEALTH_URL}"
      return 0
    fi
    sleep 1
  done
  echo "Pet-proxy did not come up (backend is unaffected). Last log lines (${PET_LOG}):" >&2
  tail -n 20 "$PET_LOG" >&2 || true
}

wait_healthy() {
  local pid="$1"
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl not found; skip health check. Log: ${LOG}"
    return 0
  fi
  for _ in $(seq 1 30); do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
      echo "Backend is up: ${HEALTH_URL}"
      return 0
    fi
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  echo "Backend failed to start. Last log lines (${LOG}):" >&2
  tail -n 30 "$LOG" >&2
  return 1
}

install_cron() {
  if ! command -v crontab >/dev/null 2>&1; then
    echo "crontab not found; watchdog and backup are not scheduled." >&2
    return 0
  fi
  local current wanted
  current="$(crontab -l 2>/dev/null || true)"
  wanted="* * * * * bash \"$ROOT/start_dev.sh\" ensure >/dev/null 2>&1 $CRON_TAG
30 3 * * * bash \"$ROOT/backup.sh\" >>\"$ROOT/repository/logs/backup.log\" 2>&1 $CRON_TAG"
  [ "$(grep -F "$CRON_TAG" <<<"$current" || true)" = "$wanted" ] && return 0
  { grep -vF "$CRON_TAG" <<<"$current" || true; echo "$wanted"; } | grep -v '^$' | crontab -
  echo "Cron installed: watchdog every minute, backup daily at 03:30."
}

case "$ACTION" in
  status)
    echo "Parent dir: ${PARENT}; backend tcp port: ${PORT}; pet-proxy tcp port: ${PET_PORT}"
    [ -f "$STOP_MARK" ] && echo "Stopped manually (watchdog paused) since $(date -r "$STOP_MARK" '+%F %T')."
    PET="$(pet_pids)"
    if [ -n "$PET" ]; then echo "Pet-proxy running (PID $(echo $PET)). Log: ${PET_LOG}"; else echo "Pet-proxy stopped."; fi
    PIDS="$(backend_pids)"
    if [ -z "$PIDS" ]; then
      echo "Backend stopped."
      exit 1
    fi
    echo "Backend running (PID $(echo $PIDS)). Log: ${LOG}"
    if command -v curl >/dev/null 2>&1; then
      curl -fsS "$HEALTH_URL" && echo || echo "Health check failed: ${HEALTH_URL}" >&2
    fi
    exit 0
    ;;
  stop)
    touch "$STOP_MARK"
    stop_backend
    stop_pet
    echo "Watchdog paused until next restart."
    exit 0
    ;;
  ensure)
    # Cron watchdog: start the backend / pet-proxy if down, each at most once every 5 minutes.
    [ -f "$STOP_MARK" ] && exit 0
    if [ -f "$ROOT/pet-proxy/server.py" ] && [ -z "$(pet_pids)" ] && [ -z "$(find "$PET_ENSURE_MARK" -mmin -5 2>/dev/null)" ]; then
      touch "$PET_ENSURE_MARK"
      echo "[$(date '+%F %T')] watchdog: pet-proxy down on tcp:${PET_PORT}, starting" >>"$PET_LOG"
      start_pet >>"$PET_LOG" 2>&1
    fi
    [ -n "$(backend_pids)" ] && exit 0
    [ -n "$(find "$ENSURE_MARK" -mmin -5 2>/dev/null)" ] && exit 0
    touch "$ENSURE_MARK"
    echo "[$(date '+%F %T')] watchdog: backend down on tcp:${PORT}, starting" >>"$LOG"
    start_backend >>"$LOG" 2>&1
    exit 0
    ;;
  cron)
    install_cron
    crontab -l | grep -F "$CRON_TAG"
    exit 0
    ;;
esac

echo "Parent dir: ${PARENT}; backend tcp port: ${PORT}; pet-proxy tcp port: ${PET_PORT}"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm not found. Install example: npm install -g pnpm --prefix \"\$HOME/.local\"" >&2
  exit 1
fi

source "$(conda_base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV"

python "$ROOT/ensure_deps.py"

echo "Building frontend..."
(cd "$ROOT/bbctg_vita_web" && pnpm -F @bbctg/antibody-vita run build)

stop_backend
stop_pet
rm -f "$STOP_MARK" "$ENSURE_MARK" "$PET_ENSURE_MARK"
install_cron
start_pet
start_backend
wait_healthy "$BACKEND_PID"
wait_pet
