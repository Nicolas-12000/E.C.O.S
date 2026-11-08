-- Centroides para mapa de movilidad (dashboard Deck.gl). Idempotente.

ALTER TABLE public.dim_departamentos
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

UPDATE public.dim_departamentos SET latitude = 6.2518, longitude = -75.5636 WHERE departamento_code = '05' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 10.9639, longitude = -74.7964 WHERE departamento_code = '08' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.7110, longitude = -74.0721 WHERE departamento_code = '11' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 10.3910, longitude = -75.4794 WHERE departamento_code = '13' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 5.5353, longitude = -73.3678 WHERE departamento_code = '15' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 5.0703, longitude = -75.5138 WHERE departamento_code = '17' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 1.6142, longitude = -75.6062 WHERE departamento_code = '18' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 2.4448, longitude = -76.6147 WHERE departamento_code = '19' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 9.3373, longitude = -73.6536 WHERE departamento_code = '20' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 8.7479, longitude = -75.8814 WHERE departamento_code = '23' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.6097, longitude = -74.0817 WHERE departamento_code = '25' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 5.6947, longitude = -76.6611 WHERE departamento_code = '27' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 2.5359, longitude = -75.5277 WHERE departamento_code = '41' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 11.5444, longitude = -72.9073 WHERE departamento_code = '44' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 10.4113, longitude = -74.4057 WHERE departamento_code = '47' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.1420, longitude = -73.6268 WHERE departamento_code = '50' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 1.2136, longitude = -77.2811 WHERE departamento_code = '52' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 7.9465, longitude = -72.8988 WHERE departamento_code = '54' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.5339, longitude = -75.6811 WHERE departamento_code = '63' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.8133, longitude = -75.6961 WHERE departamento_code = '66' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 6.6437, longitude = -73.6538 WHERE departamento_code = '68' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 9.3047, longitude = -75.3978 WHERE departamento_code = '70' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.4389, longitude = -75.2322 WHERE departamento_code = '73' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 3.4516, longitude = -76.5320 WHERE departamento_code = '76' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 7.0762, longitude = -70.7105 WHERE departamento_code = '81' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 5.7589, longitude = -71.5724 WHERE departamento_code = '85' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 0.8280, longitude = -77.6406 WHERE departamento_code = '86' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 12.5847, longitude = -81.7006 WHERE departamento_code = '88' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = -1.4429, longitude = -71.5724 WHERE departamento_code = '91' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 2.5853, longitude = -72.0762 WHERE departamento_code = '94' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 2.5689, longitude = -72.6387 WHERE departamento_code = '95' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 1.2019, longitude = -70.8110 WHERE departamento_code = '97' AND latitude IS NULL;
UPDATE public.dim_departamentos SET latitude = 4.4230, longitude = -69.2878 WHERE departamento_code = '99' AND latitude IS NULL;
