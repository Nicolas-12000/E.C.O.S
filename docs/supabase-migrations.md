# Migraciones Supabase (ECOS)

Los datos operativos ya cargados (`fact_core_weekly`, dimensiones, etc.) **no se recrean** con estas migraciones. Solo se añaden tablas nuevas para pronósticos semanales versionados.

## Orden de aplicación

| Archivo | Qué hace | Depende de |
|---|---|---|
| `scripts/supabase_init_01.sql` | Extensiones + `dim_departamentos`, `dim_municipios` | — |
| `scripts/supabase_init_02.sql` | Hechos: `fact_core_weekly`, clima, vacunación, promedios | Part 1 |
| `scripts/supabase_init_03.sql` | RAG / señales RSS | Part 1 |
| `supabase/migrations/0001_add_predictions_table.sql` | Tabla legacy `public.predictions` (chat, API `/predictions`) | Hechos opcional |
| `supabase/migrations/0002_prediction_runs.sql` | `prediction_runs` + `prediction_points` (corrida semanal) | `dim_municipios` recomendado (JOIN nombres) |
| `supabase/migrations/0003_prediction_model_family.sql` | Columna `model_family` (naive/ridge/hybrid) | 0002 |

Si la base **ya existe** en Supabase (tu caso), aplica solo lo que falte:

```bash
# Desde la raíz del repo, con SUPABASE_DB_URL en .env
psql "$SUPABASE_DB_URL" -f supabase/migrations/0002_prediction_runs.sql
```

`0001` solo si aún no tienes `public.predictions`.

## Modelo de pronóstico

```
prediction_runs (1 fila por job semanal)
    run_id, model_name, as_of_*  ← última semana con casos observados en fact_core_weekly
         │
         └── prediction_points (N filas)
                 municipio × disease × horizon_weeks (1–4)
```

- **`as_of_*`**: ancla epidemiológica; no inventa semanas entre el cierre de SIVIGILA y hoy.
- **`horizon_weeks`**: cuántas semanas adelante del ancla es cada fila.
- La tabla **`predictions`** sigue existiendo como espejo de horizonte 1 para el chat (`sync_legacy_predictions_table`).

## Validación del gold en BD

```bash
.venv/bin/python scripts/validate_gold_contract.py --supabase
```

Comprueba clave única `(epi_year, epi_week, municipio_code, disease)` y `cases_total >= 0` en `fact_core_weekly`.

## Job semanal

```bash
.venv/bin/python scripts/weekly_forecast_job.py --limit 200
```

Opciones: `--skip-signals`, `--skip-validate`. Requiere modelo `models/final_model.joblib` y `SUPABASE_DB_URL`.
