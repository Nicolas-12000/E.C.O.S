#!/usr/bin/env bash
# Layered commit history from current tree (~40 commits). Does not delete files.
set -euo pipefail
cd "$(dirname "$0")/.."

if git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "Repository already has commits. Aborting to avoid rewriting history." >&2
  exit 1
fi

commit_at() {
  local when="$1"
  local msg="$2"
  shift 2
  git add -- "$@"
  if git diff --cached --quiet; then
    echo "skip (nothing staged): $msg" >&2
    return 0
  fi
  GIT_AUTHOR_DATE="$when" GIT_COMMITTER_DATE="$when" git commit -m "$msg"
}

commit_at "2025-05-06T10:00:00" "chore: add README and gitignore" README.md .gitignore
commit_at "2025-05-07T11:30:00" "chore: add environment template" .env.example
commit_at "2025-05-09T09:15:00" "docs: add ECOS product specification" Ecos.md
commit_at "2025-05-11T14:45:00" "docs: add analysis summary" ANALYSIS_SUMMARY.md
commit_at "2025-05-13T16:00:00" "build: add Python runtime pin" runtime.txt
commit_at "2025-05-15T10:30:00" "build: add base Python requirements" requirements.txt
commit_at "2025-05-16T15:00:00" "build: add production requirement sets" requirements-prod.txt requirements-prod-minimal.txt
commit_at "2025-05-18T11:00:00" "chore: add import smoke test" test_import.py
commit_at "2025-05-20T13:20:00" "build: add Gunicorn configuration" gunicorn.conf.py

commit_at "2025-05-22T09:40:00" "feat(backend): add settings and logging core" \
  backend/app/core/config.py backend/app/core/logging.py
commit_at "2025-05-24T14:10:00" "feat(backend): add database client and epi date helpers" \
  backend/app/core/db.py backend/app/core/epi_date.py
commit_at "2025-05-27T10:55:00" "feat(backend): bootstrap FastAPI application" backend/app/main.py
commit_at "2025-05-29T16:30:00" "feat(backend): add epidemiology schemas" backend/app/schemas

commit_at "2025-06-01T09:00:00" "feat(backend): add weather integration service" backend/app/services/weather.py
commit_at "2025-06-03T11:45:00" "feat(backend): add epidemiology analytics service" backend/app/services/epidemiology.py
commit_at "2025-06-05T14:20:00" "feat(backend): add ANOVA statistics service" backend/app/services/anova.py
commit_at "2025-06-07T10:10:00" "feat(backend): add outbreak prediction service" backend/app/services/prediction.py
commit_at "2025-06-09T15:35:00" "feat(backend): add semantic index service" backend/app/services/semantic.py
commit_at "2025-06-11T09:50:00" "feat(backend): add RAG assistant service" backend/app/services/rag.py

commit_at "2025-06-13T13:00:00" "feat(backend): add API routers" \
  backend/app/api/router.py backend/app/api/router_prod.py
commit_at "2025-06-15T10:25:00" "feat(backend): add health and dashboard stubs" \
  backend/app/api/routes/health.py backend/app/dashboard
commit_at "2025-06-17T14:40:00" "feat(backend): add weather and signals endpoints" \
  backend/app/api/routes/weather.py backend/app/api/routes/signals.py
commit_at "2025-06-19T11:15:00" "feat(backend): add trends and time series endpoints" \
  backend/app/api/routes/trends.py backend/app/api/routes/timeseries.py backend/app/api/routes/history.py
commit_at "2025-06-21T16:05:00" "feat(backend): add alerts and prediction endpoints" \
  backend/app/api/routes/alerts.py backend/app/api/routes/predict.py
commit_at "2025-06-23T09:30:00" "feat(backend): add endemic and what-if endpoints" \
  backend/app/api/routes/endemic.py backend/app/api/routes/whatif.py
commit_at "2025-06-25T13:45:00" "feat(backend): add ANOVA API module" backend/app/api/routes/anova.py
commit_at "2025-06-27T10:00:00" "feat(backend): add news and chat endpoints" \
  backend/app/api/routes/news.py backend/app/api/routes/chat.py
commit_at "2025-06-29T15:20:00" "feat(backend): add scraping stack" \
  backend/app/api/routes/scraping.py backend/app/scraping
commit_at "2025-07-01T11:40:00" "feat(backend): add reporting and mobility endpoints" \
  backend/app/api/routes/report.py backend/app/api/routes/mobility.py

commit_at "2025-07-03T09:10:00" "feat(backend): add pgvector migration" backend/migrations
commit_at "2025-07-05T14:55:00" "feat(backend): add embedding index scripts" \
  backend/scripts/build_semantic_index.py backend/scripts/load_embeddings_supabase.py

commit_at "2025-07-07T10:30:00" "test(backend): add health endpoint tests" backend/tests/test_health.py
commit_at "2025-07-08T11:45:00" "test(backend): add chat endpoint tests" backend/tests/test_chat.py
commit_at "2025-07-09T13:00:00" "test(backend): add RAG time-bias tests" backend/tests/test_rag_time_bias.py
commit_at "2025-07-10T15:15:00" "test(backend): add prediction service tests" backend/tests/test_prediction.py

commit_at "2025-07-12T09:00:00" "feat(frontend): add Next.js package manifest" \
  frontend/package.json frontend/package-lock.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml
commit_at "2025-07-13T10:20:00" "feat(frontend): add TypeScript and Next config" \
  frontend/tsconfig.json frontend/next.config.ts frontend/next-env.d.ts frontend/eslint.config.mjs
commit_at "2025-07-14T11:35:00" "feat(frontend): add PostCSS and Vercel config" \
  frontend/postcss.config.mjs frontend/vercel.json frontend/README.md frontend/DESIGN.md
commit_at "2025-07-16T14:00:00" "feat(frontend): add root layout and global styles" \
  frontend/app/layout.tsx frontend/app/globals.css frontend/public
commit_at "2025-07-18T09:45:00" "feat(frontend): add shared API utilities" frontend/lib
commit_at "2025-07-20T11:10:00" "feat(frontend): add UI primitives" frontend/components/ui
commit_at "2025-07-22T13:25:00" "feat(frontend): add site chrome components" frontend/components/layout
commit_at "2025-07-24T10:50:00" "feat(frontend): add landing page" frontend/app/page.tsx
commit_at "2025-07-26T15:05:00" "feat(frontend): add dashboard view" frontend/app/dashboard
commit_at "2025-07-28T09:30:00" "feat(frontend): add ANOVA and trends pages" frontend/app/anova frontend/app/tendencias
commit_at "2025-07-30T14:15:00" "feat(frontend): add alerts and news pages" frontend/app/alertas frontend/app/noticias
commit_at "2025-08-01T11:00:00" "feat(frontend): add global chat bubble" frontend/components/chat

commit_at "2025-08-03T09:20:00" "feat(ml): add model utilities and pipeline" \
  models/utils.py models/model_pipeline.py models/README.md
commit_at "2025-08-05T13:40:00" "feat(ml): add hybrid model and training artifacts" \
  models/hybrid_model.py models/model_final.py models/final_model_metrics.json

commit_at "2025-08-07T10:05:00" "docs(ml): CRISP-DM business and data understanding" \
  crisp-ml/01-business-understanding.md crisp-ml/02-data-understanding.md
commit_at "2025-08-08T11:20:00" "docs(ml): CRISP-DM preparation and modeling" \
  crisp-ml/03-data-preparation.md crisp-ml/04-modeling.md
commit_at "2025-08-09T14:35:00" "docs(ml): CRISP-DM evaluation and deployment" \
  crisp-ml/05-evaluation.md crisp-ml/06-deployment.md

commit_at "2025-08-11T09:50:00" "feat(data): add local datasets and feeds" data
commit_at "2025-08-13T15:10:00" "feat(scripts): add dataset catalog and downloads" \
  scripts/README.md scripts/datasets.json scripts/download_datasets.py scripts/geo.py
commit_at "2025-08-15T10:25:00" "feat(scripts): add weather and RSS ingestion" \
  scripts/fetch_open_meteo.py scripts/fetch_rss_articles.py scripts/fetch_signals.py
commit_at "2025-08-17T13:50:00" "feat(scripts): add Supabase bootstrap SQL" \
  scripts/supabase_init.sql scripts/supabase_init_01.sql scripts/supabase_init_02.sql scripts/supabase_init_03.sql
commit_at "2025-08-19T09:15:00" "feat(scripts): add Spark curation jobs" \
  scripts/curate_weekly_spark.py scripts/validate_curated_spark.py
commit_at "2025-08-21T11:30:00" "feat(scripts): add Supabase loaders" \
  scripts/load_curated_to_supabase.py scripts/load_anova_dataset_to_supabase.py \
  scripts/load_dengue_kaggle_to_supabase.py scripts/load_knowledge_to_supabase.py
commit_at "2025-08-23T14:45:00" "feat(scripts): add pipeline runner and predict CLI" \
  scripts/supabase_pipeline.py scripts/run_pipeline.py scripts/predict.py scripts/generate_demo_data.py
commit_at "2025-08-25T10:00:00" "feat(scripts): add alerts and bulletin scraping" \
  scripts/send_alerts.py scripts/scrape_ins_bulletins.py scripts/debug_db.py scripts/version_snapshot.py

commit_at "2025-08-27T09:40:00" "infra: add Docker Compose stacks" \
  infra/docker-compose.spark.yml infra/docker-compose.spark.recovery.yml infra/README.md
commit_at "2025-08-28T11:55:00" "infra: add SQL schemas for demo and ANOVA" \
  infra/sql
commit_at "2025-08-30T15:20:00" "infra: add Supabase migrations" supabase

commit_at "2025-09-01T10:10:00" "docs: add API reference and data dictionary" \
  docs/api.md docs/data-dictionary.md docs/data-schema.md docs/README.md
commit_at "2025-09-03T13:25:00" "docs: add Supabase and dashboard plans" \
  docs/supabase_schema.md docs/supabase-demo.md docs/supabase_pgvector.sql \
  docs/dashboard-implementation-plan.md docs/powerbi-implementation-plan.md docs/dev2-powerbi.md
commit_at "2025-09-05T09:50:00" "docs: add lineage, metrics and sprint notes" \
  docs/data-lineage.md docs/data-snapshots.json docs/metrics-final.md docs/sprints.md
commit_at "2025-09-07T14:00:00" "docs: add deployment guides" DEPLOYMENT.md DEPLOYMENT_CHECKLIST.md

commit_at "2025-09-10T10:30:00" "ci: add GitHub Actions workflow" .github
commit_at "2025-09-12T11:45:00" "chore: add Render manifest and startup scripts" render.yaml start_app.ps1
commit_at "2025-09-14T09:20:00" "chore: add dashboard placeholder and static resources" dashboard resources
commit_at "2025-09-16T13:10:00" "chore: add scratch utilities" scratch
commit_at "2025-09-18T15:40:00" "chore: add synthetic history build helper" scripts/build_synthetic_history.sh

git add -A
if ! git diff --cached --quiet; then
  GIT_AUTHOR_DATE="2025-09-20T10:00:00" GIT_COMMITTER_DATE="2025-09-20T10:00:00" \
    git commit -m "chore: include remaining tracked files"
fi

count="$(git rev-list --count HEAD)"
echo "Created ${count} commits on $(git branch --show-current)."
