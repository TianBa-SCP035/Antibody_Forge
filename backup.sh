#!/usr/bin/env bash
# Back up the main database and uploaded files: ./backup.sh
# Database: daily mysqldump kept 14 days, Sunday copies kept 8 weeks.
# Files: repository/uploads and repository/order_sync mirrored without deleting removed files.
# BACKUP_DIR defaults to ~/backups/antibody_forge/<test|prod> (outside the repo), so both environments on one host never share files.

set -euo pipefail
export PATH="/usr/bin:/bin:/usr/local/bin:${PATH}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT="$(basename "$(dirname "$ROOT")")"
APP_ENV="$([ "$PARENT" = "prod" ] && echo prod || echo test)"
ENV_FILE="${VITA_SERVER_ENV_FILE:-$ROOT/config/$APP_ENV/vita_server.env}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/antibody_forge/$APP_ENV}"
KEEP_DAILY_DAYS="${KEEP_DAILY_DAYS:-14}"
KEEP_WEEKLY_DAYS="${KEEP_WEEKLY_DAYS:-56}"
STAMP="$(date '+%Y%m%d_%H%M')"

log() { echo "[$(date '+%F %T')] $*"; }

command -v mysqldump >/dev/null 2>&1 || { log "mysqldump not found; install: sudo apt install -y default-mysql-client"; exit 1; }
command -v python3 >/dev/null 2>&1 || { log "python3 not found"; exit 1; }
[ -f "$ENV_FILE" ] || { log "env file not found: $ENV_FILE"; exit 1; }

mkdir -p "$BACKUP_DIR/db/daily" "$BACKUP_DIR/db/weekly" "$BACKUP_DIR/files"
chmod 700 "$BACKUP_DIR"

CNF="$(mktemp)"
trap 'rm -f "$CNF" "$BACKUP_DIR/db/daily/.partial.sql.gz"' EXIT
chmod 600 "$CNF"

# Credentials go to a 600 temp file so the password never appears in the process list.
DB_NAME="$(python3 - "$ENV_FILE" "$CNF" <<'PY'
import sys
from urllib.parse import unquote, urlsplit

env_file, cnf = sys.argv[1], sys.argv[2]
url = ""
for line in open(env_file, encoding="utf-8"):
    line = line.strip()
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip().strip("'\"")
if not url:
    sys.exit("DATABASE_URL missing in env file")
parts = urlsplit(url)
password = unquote(parts.password or "").replace("\\", "\\\\").replace('"', '\\"')
with open(cnf, "w", encoding="utf-8") as fh:
    fh.write("[client]\n")
    fh.write(f"user={unquote(parts.username or '')}\n")
    fh.write(f'password="{password}"\n')
    fh.write(f"host={parts.hostname or 'localhost'}\n")
    fh.write(f"port={parts.port or 3306}\n")
print(parts.path.lstrip("/"))
PY
)"

DUMP_OPTS=(--single-transaction --quick --triggers --hex-blob --no-tablespaces --default-character-set=utf8mb4)
HELP="$(mysqldump --help 2>/dev/null || true)"
grep -q -- '--set-gtid-purged' <<<"$HELP" && DUMP_OPTS+=(--set-gtid-purged=OFF)
grep -q -- '--column-statistics' <<<"$HELP" && DUMP_OPTS+=(--column-statistics=0)

PARTIAL="$BACKUP_DIR/db/daily/.partial.sql.gz"
TARGET="$BACKUP_DIR/db/daily/${DB_NAME}_${STAMP}.sql.gz"
log "dumping database ${DB_NAME}"
mysqldump --defaults-extra-file="$CNF" "${DUMP_OPTS[@]}" "$DB_NAME" | gzip -6 >"$PARTIAL"
gzip -t "$PARTIAL"
mv "$PARTIAL" "$TARGET"
log "database saved: $TARGET ($(du -h "$TARGET" | cut -f1))"

if [ "$(date +%u)" = "7" ]; then
  cp "$TARGET" "$BACKUP_DIR/db/weekly/"
fi
find "$BACKUP_DIR/db/daily" -name "${DB_NAME}_*.sql.gz" -mtime +"$((KEEP_DAILY_DAYS - 1))" -delete
find "$BACKUP_DIR/db/weekly" -name "${DB_NAME}_*.sql.gz" -mtime +"$((KEEP_WEEKLY_DAYS - 1))" -delete

for dir in uploads order_sync; do
  SRC="$ROOT/repository/$dir"
  [ -d "$SRC" ] || continue
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$SRC/" "$BACKUP_DIR/files/$dir/"
  else
    mkdir -p "$BACKUP_DIR/files/$dir"
    cp -a -u "$SRC/." "$BACKUP_DIR/files/$dir/"
  fi
done
log "files synced: $BACKUP_DIR/files ($(du -sh "$BACKUP_DIR/files" | cut -f1))"
