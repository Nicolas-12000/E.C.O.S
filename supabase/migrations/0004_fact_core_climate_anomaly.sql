-- Optional gold columns: Open-Meteo actuals vs IDEAM normals (curate_weekly_spark.py)

ALTER TABLE public.fact_core_weekly
    ADD COLUMN IF NOT EXISTS humidity_avg_pct_actual DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temp_avg_c_anomaly DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS precipitation_mm_anomaly DOUBLE PRECISION;
