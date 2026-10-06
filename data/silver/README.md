# Silver layer (native grain per source)

Intermediate cleaned tables before joining into `fact_core_weekly`. Paths are produced by the Spark pipeline or Supabase loads.

| Dataset | Grain | Location |
|---|---|---|
| SIVIGILA cases (gold) | week × municipio × disease | `{prefix}_fact_cases_weekly` from curate (no exogenous cols) |
| SIVIGILA cases | week × municipio × disease | `data/processed/silver/sivigila_weekly/` (export target) |
| IDEAM climate normals | month × municipio | `fact_climate_monthly` in Supabase |
| Vaccination | year × departamento | `fact_vaccination_annual` |
| RIPS | year × municipio × disease | optional CSV in `data/raw/` |
| Mobility nacional | week × municipio | mobility_combined CSV from curate |
| Signals trends | week × departamento × disease | `{prefix}_silver_signals_trends_dept` from curate |
| Signals RSS | week × departamento × disease | `{prefix}_silver_signals_rss_dept` from curate |
| Signals (legacy) | week × departamento (or national) | `data/processed/signals_*.csv` |

Gold cases-only export: `scripts/export_gold_cases.py --supabase` or curate `fact_cases_weekly`.

ML wide table: `python scripts/build_feature_store.py` joins gold + silver signals at department grain.

Curate keeps Trends/RSS out of `fact_core_weekly` by default; use `--embed-signals-in-gold` only for legacy wide loads.
