#!/usr/bin/env bash
# Export ecos-api | ecos-data | ecos-front from this monorepo with full git history (git filter-repo).
# Workflow: keep developing in ECOS; run this before delivery or when child remotes need updating.
#
#   pip install git-filter-repo
#   ./scripts/export_child_repos.sh --output ~/exports/ecos-children
#   ./scripts/export_child_repos.sh --output ~/exports/ecos-children --push
#
# Env (optional, for --push):
#   ECOS_API_REMOTE   e.g. git@github.com:USER/ecos-api.git
#   ECOS_DATA_REMOTE  e.g. git@github.com:USER/ecos-data.git
#   ECOS_FRONT_REMOTE e.g. git@github.com:USER/ecos-front.git

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT=""
DRY_RUN=false
DO_PUSH=false

usage() {
  sed -n '1,20p' "$0" | tail -n +2
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --push) DO_PUSH=true; shift ;;
    *) echo "[error] unknown arg: $1" >&2; usage 1 ;;
  esac
done

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="${ROOT}/../ecos-children-export"
fi

if ! command -v git-filter-repo &>/dev/null; then
  echo "[error] install git-filter-repo:  pip install git-filter-repo" >&2
  exit 1
fi

if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  echo "[warn] monorepo has uncommitted changes; child history will not include them until you commit." >&2
fi

# Paths kept per child (commits touching any of these appear in that child's history).
API_PATHS=(
  backend/
  models/
  supabase/
  requirements-dev.txt
  requirements-prod.txt
  requirements-prod-minimal.txt
  requirements.txt
  gunicorn.conf.py
  render.yaml
  DEPLOYMENT.md
  DEPLOYMENT_CHECKLIST.md
  .env.example
  .gitignore
  scripts/migrate_supabase.py
  scripts/migrate_supabase.sh
  scripts/weekly_forecast_job.py
  scripts/train_model_ladder.py
  scripts/validate_gold_contract.py
  scripts/build_feature_store.py
  scripts/predict.py
  scripts/debug_db.py
  scripts/send_alerts.py
)

DATA_PATHS=(
  data/
  infra/
  scripts/curate_weekly_spark.py
  scripts/download_datasets.py
  scripts/load_curated_to_supabase.py
  scripts/load_dengue_kaggle_to_supabase.py
  scripts/load_anova_dataset_to_supabase.py
  scripts/load_knowledge_to_supabase.py
  scripts/export_gold_cases.py
  scripts/run_pipeline.py
  scripts/datasets.json
  scripts/validate_curated_spark.py
  scripts/supabase_pipeline.py
  scripts/supabase_init.sql
  scripts/supabase_init_01.sql
  scripts/supabase_init_02.sql
  scripts/supabase_init_03.sql
  scripts/fetch_open_meteo.py
  scripts/fetch_signals.py
  scripts/fetch_rss_articles.py
  scripts/generate_demo_data.py
  scripts/scrape_ins_bulletins.py
  scripts/geo.py
  scripts/version_snapshot.py
  scripts/README.md
  .gitignore
)

FRONT_PATHS=(
  frontend/
  .gitignore
)

filter_paths() {
  local dest="$1"
  shift
  local -a paths=("$@")
  local -a args=()
  for p in "${paths[@]}"; do
    if [[ -e "$ROOT/$p" ]] || git -C "$ROOT" cat-file -e "HEAD:$p" 2>/dev/null; then
      args+=(--path "$p")
    fi
  done
  if [[ ${#args[@]} -eq 0 ]]; then
    echo "[error] no paths found for $dest" >&2
    return 1
  fi
  rm -rf "$dest"
  mkdir -p "$(dirname "$dest")"
  git clone --no-local "$ROOT" "$dest"
  (
    cd "$dest"
    git filter-repo --force "${args[@]}"
  )
}

write_child_readme() {
  local dest="$1"
  local title="$2"
  local body="$3"
  if [[ -f "$dest/README.md" ]]; then
    mv "$dest/README.md" "$dest/README.monorepo.md"
  fi
  cat >"$dest/README.md" <<EOF
# $title

Repo exportado desde el monorepo **ECOS** (historial filtrado con \`scripts/export_child_repos.sh\`).
Desarrollo principal: monorepo ECOS.

$body
EOF
}

export_one() {
  local name="$1"
  local dest="$OUTPUT/$name"
  shift
  echo "[export] $name -> $dest"
  if $DRY_RUN; then
    echo "  paths: $*"
    return 0
  fi
  filter_paths "$dest" "$@"
}

main() {
  mkdir -p "$OUTPUT"
  export_one ecos-api "${API_PATHS[@]}"
  export_one ecos-data "${DATA_PATHS[@]}"
  export_one ecos-front "${FRONT_PATHS[@]}"

  if $DRY_RUN; then
    echo "[dry-run] would write to $OUTPUT"
    exit 0
  fi

  write_child_readme "$OUTPUT/ecos-api" "ECOS API" "$(cat <<'EOF'
## Arranque
\`\`\`bash
pip install -r requirements-dev.txt
cp .env.example .env   # SUPABASE_DB_URL, GROQ_API_KEY
python scripts/migrate_supabase.py
cd backend && uvicorn app.main:app --reload
\`\`\`
EOF
)"

  write_child_readme "$OUTPUT/ecos-data" "ECOS Data" "$(cat <<'EOF'
## Pipeline (resumen)
\`\`\`bash
python scripts/download_datasets.py
docker compose -f infra/docker-compose.spark.yml up -d
# curate → load_curated_to_supabase.py
\`\`\`
EOF
)"

  write_child_readme "$OUTPUT/ecos-front" "ECOS Frontend" "$(cat <<'EOF'
## Arranque
\`\`\`bash
cd frontend  # raíz = frontend en este repo
npm install
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > frontend/.env.local
npm run dev
\`\`\`
Nota: si el repo solo contiene \`frontend/\`, ejecuta comandos dentro de \`frontend/\`.
EOF
)"

  if $DO_PUSH; then
    push_repo "$OUTPUT/ecos-api" "${ECOS_API_REMOTE:-}"
    push_repo "$OUTPUT/ecos-data" "${ECOS_DATA_REMOTE:-}"
    push_repo "$OUTPUT/ecos-front" "${ECOS_FRONT_REMOTE:-}"
  fi

  echo "[ok] Children in $OUTPUT"
  echo "     Next: create GitHub repos and push, or run with ECOS_*_REMOTE set and --push"
}

push_repo() {
  local dir="$1"
  local remote="$2"
  if [[ -z "$remote" ]]; then
    echo "[skip] push $dir (remote not set)"
    return 0
  fi
  (
    cd "$dir"
    git remote remove origin 2>/dev/null || true
    git remote add origin "$remote"
    git push -u origin main --force
  )
  echo "[push] $remote"
}

main
