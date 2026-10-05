-- Weekly forecast runs (operational predictions anchored on last observed week)

CREATE TABLE IF NOT EXISTS public.prediction_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    as_of_epi_year INTEGER NOT NULL,
    as_of_epi_week INTEGER NOT NULL,
    as_of_week_start_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_prediction_runs_created_at
    ON public.prediction_runs (created_at DESC);

CREATE TABLE IF NOT EXISTS public.prediction_points (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES public.prediction_runs (run_id) ON DELETE CASCADE,
    municipio_code VARCHAR(5) NOT NULL,
    departamento_code VARCHAR(2),
    disease VARCHAR(50) NOT NULL,
    horizon_weeks INTEGER NOT NULL CHECK (horizon_weeks BETWEEN 1 AND 4),
    epi_year INTEGER NOT NULL,
    epi_week INTEGER NOT NULL,
    week_start_date DATE,
    predicted_cases DOUBLE PRECISION NOT NULL,
    outbreak_flag BOOLEAN NOT NULL DEFAULT FALSE,
    outbreak_threshold DOUBLE PRECISION,
    endemic_risk VARCHAR(20),
    shap_top_factors JSONB,
    UNIQUE (run_id, municipio_code, disease, horizon_weeks)
);

CREATE INDEX IF NOT EXISTS idx_prediction_points_run_outbreak
    ON public.prediction_points (run_id, outbreak_flag, predicted_cases DESC);

CREATE INDEX IF NOT EXISTS idx_prediction_points_lookup
    ON public.prediction_points (municipio_code, disease, epi_year, epi_week);
