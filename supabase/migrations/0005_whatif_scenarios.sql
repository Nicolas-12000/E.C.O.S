-- Persisted what-if simulations from POST /whatif (optional save_scenario=true)

CREATE TABLE IF NOT EXISTS public.whatif_scenarios (
    scenario_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    municipio_code VARCHAR(5) NOT NULL,
    disease VARCHAR(50) NOT NULL,
    weeks_ahead INTEGER NOT NULL CHECK (weeks_ahead BETWEEN 1 AND 4),
    adjustments JSONB NOT NULL DEFAULT '{}'::jsonb,
    delta_total DOUBLE PRECISION,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_whatif_scenarios_created
    ON public.whatif_scenarios (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_whatif_scenarios_muni_disease
    ON public.whatif_scenarios (municipio_code, disease);
