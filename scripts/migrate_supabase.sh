#!/usr/bin/env bash
# Apply all supabase/migrations/*.sql in lexical order (0001 … 0005).
# Usage from repo root:  bash scripts/migrate_supabase.sh
# Optional fresh DB:     bash scripts/migrate_supabase.sh --with-init

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WITH_INIT=false
if [[ "${1:-}" == "--with-init" ]]; then
  WITH_INIT=true
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

URL="${SUPABASE_DB_URL:-${DATABASE_URL:-}}"
if [[ -z "$URL" ]]; then
  echo "[error] Set SUPABASE_DB_URL or DATABASE_URL in .env" >&2
  exit 1
fi

if ! command -v psql &>/dev/null; then
  echo "[info] psql not found — using Python (psycopg) instead"
  exec python3 "$ROOT/scripts/migrate_supabase.py" "$([[ "$WITH_INIT" == true ]] && echo --with-init)"
fi

run_sql() {
  local file="$1"
  echo "[migrate] $(basename "$file")"
  psql "$URL" -v ON_ERROR_STOP=1 -f "$file"
}

if [[ "$WITH_INIT" == true ]]; then
  for f in "$ROOT"/scripts/supabase_init_0{1,2,3}.sql; do
    [[ -f "$f" ]] && run_sql "$f"
  done
fi

shopt -s nullglob
files=("$ROOT"/supabase/migrations/*.sql)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "[error] No files in supabase/migrations/" >&2
  exit 1
fi
IFS=$'\n' sorted=($(sort <<<"${files[*]}"))
unset IFS
for f in "${sorted[@]}"; do
  run_sql "$f"
done

echo "[ok] Supabase migrations applied."
