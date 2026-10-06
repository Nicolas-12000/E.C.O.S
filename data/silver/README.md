# Silver layer (native grain per source)

Intermediate cleaned tables before joining into `fact_core_weekly`. Paths are produced by the Spark pipeline or Supabase loads.

| Dataset | Grain | Location |
|---|---|---|
| SIVIGILA cases | week × municipio × disease | `data/processed/silver/sivigila_weekly/` (export target) |
| IDEAM climate normals | month × municipio | `fact_climate_monthly` in Supabase |
| Vaccination | year × departamento | `fact_vaccination_annual` |
| RIPS | year × municipio × disease | optional CSV in `data/raw/` |
| Mobility nacional | week × municipio | mobility_combined CSV from curate |
| Signals | week × departamento (or national) | `data/processed/signals_*.csv` |

Gold cases-only export: `scripts/export_gold_cases.py --supabase`.
