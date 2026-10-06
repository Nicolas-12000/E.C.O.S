# Plan progress (execution + data + polish)

Last updated: 2026-10-05. Reference: `docs/plan.md` (local, gitignored), canvases *ecos-data-plan* and *ecos-polish-plan*.

## Summary

| Area | Done | Partial | Not started |
|---|---:|---:|---:|
| plan.md (5 blocks) | 4 | 1 | 0 |
| Data plan (canvas) | 6 | 2 | 1 |
| Polish plan (canvas) | 8 | 1 | 2 |
| **Overall** | **~82%** | | |

## plan.md

| Item | Status | Notes |
|---|---|---|
| Gold contract validation | Done | `scripts/validate_gold_contract.py` (+ Supabase) |
| Silver per source | Partial | dept signals CSV + `fact_cases_weekly` export; wide gold optional |
| Gold cases-only | Partial | `fact_cases_weekly` + `export_gold_cases.py`; Supabase still wide until reload |
| Naive / Ridge / hybrid ladder | Done | `scripts/train_model_ladder.py`, `models/metrics.json`, registry |
| Serve hybrid only if beats Ridge | Done | `model_registry.get_served_model_name()` |
| Weekly job + runs tables | Done | `weekly_forecast_job.py`, migrations 0002/0003 |
| Anchored horizons | Done | No recursive lag injection |
| Alerts from run | Done | API + `/alertas` UI |
| Landing copy vs dashboards | Done | Home → `/alertas` |
| Endemic p90 only (no fixed 5) | Done | Historic fallback uses per-muni channel p90 |
| Climate anomaly feature | Done | curate + migration `0004` |
| what-if UI + saved scenarios | Done | `/whatif`, `0005`, `whatif_store` |
| `/pronostico` + timeseries | Done | `frontend/app/pronostico/page.tsx` |
| RIPS in datasets.json | Done | |
| demo data in `data/demo` | Done | `generate_demo_data.py` |
| `predict.py` → weekly job | Done | Delegates to `weekly_forecast_job` |

## Data plan (canvas)

| Issue | Status |
|---|---|
| Chikungunya CSV unused | Open (documented; not in Y) |
| Medellín + nacional double count | Mitigated | default no UNION |
| Dedup inflates cases | Mitigated | `first()` not `sum()` + warn |
| Trends/RSS cloned to municipio | Mitigated | default no embed; `build_feature_store.py` + runtime join |
| Triple store Parquet/CSV/Supabase | Partial | by design for demo; gold export added |
| Humidity in export | Done | `humidity_avg_pct_actual` in curate + 0004 |

## Polish plan (canvas)

| Item | Status |
|---|---|
| prediction_runs / points | Done |
| Recursive horizon bug | Fixed |
| predict.py dual sink | Fixed |
| generate_demo path | Fixed |
| Prophet weekly seasonality off | Done |
| Prophet missing → None not 0 | Done |
| Ridge baseline | Done |
| what-if screen | Done |
| ANOVA on single silver table | Partial | `silver_sivigila_weekly` source (SIVIGILA-only default) |

## Your Supabase checklist

1. `psql ... -f supabase/migrations/0002_prediction_runs.sql` (if missing)
2. `psql ... -f supabase/migrations/0003_prediction_model_family.sql`
3. `psql ... -f supabase/migrations/0004_fact_core_climate_anomaly.sql`
4. `psql ... -f supabase/migrations/0005_whatif_scenarios.sql`
5. `python3 scripts/validate_gold_contract.py --supabase`
6. `python3 scripts/train_model_ladder.py` (after data/model artifact present)
7. `python3 scripts/weekly_forecast_job.py --limit 200`
8. Re-curate or `load_curated_to_supabase.py` after new gold columns if you use anomalies in ML
