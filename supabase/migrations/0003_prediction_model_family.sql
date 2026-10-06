-- Allow naive / ridge / hybrid points in the same weekly run

ALTER TABLE public.prediction_points
    ADD COLUMN IF NOT EXISTS model_family TEXT NOT NULL DEFAULT 'hybrid';

ALTER TABLE public.prediction_points
    DROP CONSTRAINT IF EXISTS prediction_points_run_id_municipio_code_disease_horizon_wee_key;

ALTER TABLE public.prediction_points
    ADD CONSTRAINT prediction_points_run_unique
    UNIQUE (run_id, municipio_code, disease, horizon_weeks, model_family);
