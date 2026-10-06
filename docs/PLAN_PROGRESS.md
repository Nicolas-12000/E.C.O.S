# Plan progress (execution + data + polish)

Last updated: 2026-10-05. Reference: `docs/plan.md` (local, gitignored), canvases *ecos-data-plan* and *ecos-polish-plan*.

## Summary

| Area | Done | Partial | Not started |
|---|---:|---:|---:|
| plan.md (5 blocks) | 3 | 1 | 1 |
| Data plan (canvas) | 4 | 3 | 2 |
| Polish plan (canvas) | 6 | 2 | 3 |
| **Overall** | **~65%** | | |

## plan.md

| Item | Status | Notes |
|---|---|---|
| Gold contract validation | Done | `scripts/validate_gold_contract.py` (+ Supabase) |
| Silver per source | Partial | `data/silver/README.md`, export gold cases; Spark still wide-table |
| Gold cases-only | Partial | `scripts/export_gold_cases.py`; Supabase `fact_core_weekly` still wide |
| Naive / Ridge / hybrid ladder | Done | `scripts/train_model_ladder.py`, `models/metrics.json`, registry |
| Serve hybrid only if beats Ridge | Done | `model_registry.get_served_model_name()` |
| Weekly job + runs tables | Done | `weekly_forecast_job.py`, migrations 0002/0003 |
| Anchored horizons | Done | No recursive lag injection |
| Alerts from run | Done | API + `/alertas` UI |
| Landing copy vs dashboards | Done | Home → `/alertas` |
| Endemic p90 only (no fixed 5) | Partial | Forecast uses channel; historic fallback still uses 5 |
| Climate anomaly feature | Not started | Still raw IDEAM + Open-Meteo columns in curate |
| what-if UI + saved scenarios | Not started | API only |
| RIPS in datasets.json | Done | |
| demo data in `data/demo` | Done | `generate_demo_data.py` |
| `predict.py` → weekly job | Done | Delegates to `weekly_forecast_job` |

## Data plan (canvas)

| Issue | Status |
|---|---|
| Chikungunya CSV unused | Open (documented; not in Y) |
| Medellín + nacional double count | Mitigated | default no UNION |
| Dedup inflates cases | Mitigated | `first()` not `sum()` + warn |
| Trends/RSS cloned to municipio | Not started | needs silver signals join at depto |
| Triple store Parquet/CSV/Supabase | Partial | by design for demo; gold export added |
| Humidity dropped from export | Not started |

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
| what-if screen | Not started |
| ANOVA on single silver table | Not started |

## Your Supabase checklist

1. `psql ... -f supabase/migrations/0002_prediction_runs.sql` (if missing)
2. `psql ... -f supabase/migrations/0003_prediction_model_family.sql`
3. `python3 scripts/validate_gold_contract.py --supabase`
4. `python3 scripts/train_model_ladder.py` (after data/model artifact present)
5. `python3 scripts/weekly_forecast_job.py --limit 200`
