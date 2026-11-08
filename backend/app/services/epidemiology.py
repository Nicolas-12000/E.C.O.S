"""
Servicio de datos epidemiológicos.
Lee el dataset curado en Parquet (o CSV como fallback) y expone
helpers para filtrar por municipio, departamento, enfermedad y semana.
No tiene lógica de predicción aquí — eso lo hace el modelo joblib.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from app.core.config import settings
from app.services.signals_join import attach_department_signals
from app.core.db import get_db_connection

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
_PARQUET_MAIN = REPO_ROOT / "data/processed/curated_weekly_parquet"
_CSV_MAIN = REPO_ROOT / "data/processed/curated_weekly_csv"
_PARQUET_FRESH = REPO_ROOT / "data/processed/curated_weekly_fresh_parquet"
_CSV_FRESH = REPO_ROOT / "data/processed/curated_weekly_fresh_csv"
_PARQUET_LEGACY = REPO_ROOT / "data/processed/curated_weekly_v0_parquet"
_CSV_LEGACY = REPO_ROOT / "data/processed/curated_weekly_v0_csv"
_MOBILITY_RAW = REPO_ROOT / "data/raw/movilidad_nacional_eh75-8ah6.csv"
_DIM_DEPARTAMENTOS = REPO_ROOT / "data/processed/curated_weekly_csv_dim_departamentos"

VALID_DISEASES = {"dengue", "chikungunya", "zika", "malaria"}
OUTBREAK_THRESHOLD = 5.0


def calculate_endemic_channel(
    municipio_code: str,
    disease: str,
    epi_week: int,
    years_window: int = 5,
    years_excluded: set[int] | None = None,
) -> dict:
    """Compute endemic channel percentiles for a municipality and ISO week."""
    if years_excluded is None:
        years_excluded = {2020, 2021}

    df = _load_df()
    if "week_start_date" not in df.columns:
        return {"p25": None, "p50": None, "p75": None, "p90": None, "n": 0}

    subset = df[
        (df["municipio_code"] == municipio_code)
        & (df["disease"] == disease)
        & (df["epi_week"] == epi_week)
        & (~df["epi_year"].isin(years_excluded))
    ].copy()

    if subset.empty:
        return {"p25": None, "p50": None, "p75": None, "p90": None, "n": 0}

    max_year = int(subset["epi_year"].max())
    min_year = max(int(subset["epi_year"].min()), max_year - years_window + 1)
    subset = subset[(subset["epi_year"] >= min_year) & (subset["epi_year"] <= max_year)]

    series = pd.to_numeric(subset["cases_total"], errors="coerce").dropna()
    if series.empty:
        return {"p25": None, "p50": None, "p75": None, "p90": None, "n": 0}

    return {
        "p25": float(series.quantile(0.25)),
        "p50": float(series.quantile(0.50)),
        "p75": float(series.quantile(0.75)),
        "p90": float(series.quantile(0.90)),
        "n": int(series.shape[0]),
    }


def classify_endemic_risk(cases_total: float, endemic_channel: dict) -> str:
    """Translate endemic percentiles into a qualitative risk level."""
    p75 = endemic_channel.get("p75")
    p90 = endemic_channel.get("p90")
    if p75 is None or p90 is None:
        return (
            "critical"
            if cases_total >= OUTBREAK_THRESHOLD * 3
            else "high" if cases_total >= OUTBREAK_THRESHOLD * 2
            else "moderate"
        )
    if cases_total >= p90:
        return "critical"
    if cases_total >= p75:
        return "high"
    if cases_total >= endemic_channel.get("p50", p75):
        return "moderate"
    return "low"


def reload_curated_cache() -> None:
    """Clear in-process cache after a new Supabase load or pipeline run."""
    _load_df.cache_clear()


def _load_df_from_supabase() -> pd.DataFrame:
    with get_db_connection() as conn:
        df = pd.read_sql("SELECT * FROM public.fact_core_weekly", conn)
    df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
    df["cases_total"] = pd.to_numeric(df["cases_total"], errors="coerce").fillna(0).astype(int)
    logger.info("Loaded curated dataset from Supabase fact_core_weekly (%s rows)", len(df))
    return attach_department_signals(df)


def get_data_as_of() -> dict | None:
    """Latest observed epidemiological week in the curated dataset."""
    try:
        df = _load_df()
    except FileNotFoundError:
        return None
    if df.empty or df["week_start_date"].isna().all():
        return None
    row = df.loc[df["week_start_date"].idxmax()]
    as_of = row["week_start_date"]
    return {
        "epi_year": int(row["epi_year"]),
        "epi_week": int(row["epi_week"]),
        "week_start_date": as_of.date() if hasattr(as_of, "date") else as_of,
    }


@lru_cache(maxsize=1)
def _load_df() -> pd.DataFrame:
    """Carga el dataset curado una vez y lo cachea en memoria."""
    db_url = settings.resolved_database_url()
    if db_url:
        try:
            return _load_df_from_supabase()
        except Exception as exc:
            logger.warning("Supabase fact_core_weekly unavailable (%s), falling back to files", exc)

    for parquet, csv_dir in [
        (_PARQUET_FRESH, _CSV_FRESH),
        (_PARQUET_MAIN, _CSV_MAIN),
        (_PARQUET_LEGACY, _CSV_LEGACY),
    ]:
        if parquet.exists():
            logger.info("Loading curated dataset from %s", parquet)
            df = pd.read_parquet(parquet)
            df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
            df["cases_total"] = pd.to_numeric(df["cases_total"], errors="coerce").fillna(0).astype(int)
            return attach_department_signals(df)
        if csv_dir.exists():
            csv_files = sorted(csv_dir.glob("*.csv"))
            if csv_files:
                logger.info("Loading curated dataset from CSV at %s", csv_dir)
                df = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
                df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
                df["cases_total"] = pd.to_numeric(df["cases_total"], errors="coerce").fillna(0).astype(int)
                return attach_department_signals(df)
    raise FileNotFoundError("Curated dataset not found. Run curate_weekly_spark.py first.")


def get_history(municipio_code: str, disease: str, limit: int = 104) -> pd.DataFrame:
    """Retorna las últimas `limit` semanas de historia para un municipio y enfermedad."""
    df = _load_df()
    mask = (df["municipio_code"] == municipio_code) & (df["disease"] == disease)
    result = df[mask].sort_values("week_start_date", ascending=False).head(limit)
    return result.reset_index(drop=True)


def get_signals(departamento_code: str, disease: str, limit: int = 52) -> pd.DataFrame:
    """
    Retorna señales tempranas (RIPS, movilidad, vacunación) a nivel departamental.
    El dataset curado agrega estas features por municipio; aquí agrupamos a depto.
    """
    df = _load_df()
    mask = (df["departamento_code"] == departamento_code) & (df["disease"] == disease)
    subset = df[mask].copy()

    signal_cols = {
        "vaccination_coverage_pct": "mean",
        "trends_score": "mean",
        "rss_mentions": "sum",
        "signals_score": "mean",
    }
    agg = {col: fn for col, fn in signal_cols.items() if col in df.columns}

    if not agg:
        return pd.DataFrame()

    grouped = (
        subset.groupby(["epi_year", "epi_week", "week_start_date", "departamento_code"])
        .agg(agg)
        .reset_index()
        .sort_values("week_start_date", ascending=False)
        .head(limit)
    )
    grouped["disease"] = disease
    return grouped.reset_index(drop=True)


def get_latest_global_summary() -> dict:
    """Retorna un resumen global de la última semana disponible en Supabase."""
    query = """
        SELECT 
            SUM(cases_total) as total_cases,
            AVG(NULLIF(temp_avg_c, 0)) as avg_temp,
            AVG(NULLIF(precipitation_mm, 0)) as avg_precip,
            epi_year, epi_week, week_start_date
        FROM public.fact_core_weekly
        GROUP BY epi_year, epi_week, week_start_date
        ORDER BY week_start_date DESC
        LIMIT 1
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                row = cur.fetchone()
                if not row:
                    return {}
                return row
    except Exception as e:
        logger.error("Error fetching global summary from DB: %s", e)
        return {}


def get_last_known_features(municipio_code: str, disease: str) -> pd.Series | Optional[pd.DataFrame]:
    """Retorna la fila más reciente del dataset para usar como input al modelo."""
    df = _load_df()
    mask = (df["municipio_code"] == municipio_code) & (df["disease"] == disease)
    subset = df[mask].sort_values("week_start_date", ascending=False)
    if subset.empty:
        return None
    return subset.iloc[0]


def _normalize_municipio_code(municipio_code: str) -> str:
    return str(municipio_code).strip().zfill(5)


def _get_mobility_from_supabase(municipio_code: str, limit: int) -> pd.DataFrame:
    muni = _normalize_municipio_code(municipio_code)
    query = """
        SELECT epi_year, epi_week, week_start_date, municipio_code,
               MAX(mobility_in) AS mobility_in,
               MAX(mobility_out) AS mobility_out,
               MAX(mobility_index) AS mobility_index
        FROM public.fact_core_weekly
        WHERE municipio_code = %s
          AND (mobility_in IS NOT NULL OR mobility_out IS NOT NULL)
        GROUP BY epi_year, epi_week, week_start_date, municipio_code
        ORDER BY week_start_date DESC
        LIMIT %s
    """
    try:
        with get_db_connection() as conn:
            df = pd.read_sql(query, conn, params=(muni, limit))
        if df.empty:
            return df
        df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
        return df.sort_values("week_start_date", ascending=True).reset_index(drop=True)
    except Exception as exc:
        logger.warning("Supabase mobility query failed for %s: %s", muni, exc)
        return pd.DataFrame()


def get_mobility(municipio_code: str, limit: int = 52) -> pd.DataFrame:
    """Retorna datos de movilidad in/out para un municipio (Supabase primero)."""
    muni = _normalize_municipio_code(municipio_code)
    if settings.resolved_database_url():
        db_df = _get_mobility_from_supabase(muni, limit)
        if not db_df.empty:
            return db_df

    df = _load_df()
    if "mobility_in" not in df.columns:
        return pd.DataFrame()

    if "municipio_code" in df.columns:
        df = df.copy()
        df["municipio_code"] = df["municipio_code"].astype(str).str.zfill(5)

    mask = df["municipio_code"] == muni
    subset = (
        df[mask]
        .groupby(["epi_year", "epi_week", "week_start_date", "municipio_code"])
        .agg({
            "mobility_in": "first",
            "mobility_out": "first",
            "mobility_index": "first",
        })
        .reset_index()
        .sort_values("week_start_date", ascending=False)
        .head(limit)
    )
    return subset.sort_values("week_start_date", ascending=True).reset_index(drop=True)


def _load_departamento_coords_from_db() -> dict[str, tuple[float, float]]:
    query = """
        SELECT departamento_code, latitude, longitude
        FROM public.dim_departamentos
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    try:
        with get_db_connection() as conn:
            rows = pd.read_sql(query, conn)
        coords: dict[str, tuple[float, float]] = {}
        for _, row in rows.iterrows():
            code = str(row["departamento_code"]).zfill(2)
            coords[code] = (float(row["latitude"]), float(row["longitude"]))
        return coords
    except Exception as exc:
        logger.warning("Could not load dim_departamentos coords from DB: %s", exc)
        return {}


def _load_departamento_coords() -> dict[str, tuple[float, float]]:
    """Centroides de departamento: Supabase dim_departamentos y/o CSV local del curado."""
    coords = _load_departamento_coords_from_db()

    if _DIM_DEPARTAMENTOS.exists():
        csv_files = sorted(_DIM_DEPARTAMENTOS.glob("*.csv"))
        if csv_files:
            df = pd.read_csv(csv_files[0])
            if "departamento_code" in df.columns:
                for _, row in df.iterrows():
                    code = str(row["departamento_code"]).zfill(2)
                    lat, lon = row.get("latitude"), row.get("longitude")
                    if pd.notna(lat) and pd.notna(lon):
                        coords[code] = (float(lat), float(lon))

    return coords


def _od_map_from_raw_csv(limit: int, coords: dict[str, tuple[float, float]]) -> pd.DataFrame:
    if not _MOBILITY_RAW.exists():
        return pd.DataFrame()

    usecols = ["MUNICIPIO_ORIGEN_RUTA", "MUNICIPIO_DESTINO_RUTA", "PASAJEROS"]
    agg: dict[tuple[str, str], float] = {}

    try:
        for chunk in pd.read_csv(_MOBILITY_RAW, usecols=usecols, chunksize=200000):
            chunk = chunk.dropna(subset=["MUNICIPIO_ORIGEN_RUTA", "MUNICIPIO_DESTINO_RUTA", "PASAJEROS"])
            chunk["origin"] = chunk["MUNICIPIO_ORIGEN_RUTA"].astype(str).str.zfill(5).str[:2]
            chunk["dest"] = chunk["MUNICIPIO_DESTINO_RUTA"].astype(str).str.zfill(5).str[:2]
            chunk = chunk[chunk["origin"] != chunk["dest"]]
            grouped = chunk.groupby(["origin", "dest"], as_index=False)["PASAJEROS"].sum()
            for _, row in grouped.iterrows():
                key = (row["origin"], row["dest"])
                agg[key] = agg.get(key, 0.0) + float(row["PASAJEROS"])
    except Exception as exc:
        logger.error("Error aggregating OD mobility CSV: %s", exc)
        return pd.DataFrame()

    return _od_pairs_to_dataframe(agg, coords, limit)


def _od_map_from_supabase(limit: int, coords: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """
    Proxy OD interdepartamental desde fact_core_weekly cuando no hay CSV nacional.
    Misma semana epi: flujo estimado ~ sqrt(salidas_origen * entradas_destino).
    """
    query = """
        WITH muni_week AS (
            SELECT departamento_code, municipio_code, epi_year, epi_week,
                   MAX(mobility_out) AS mobility_out,
                   MAX(mobility_in) AS mobility_in
            FROM public.fact_core_weekly
            WHERE mobility_in IS NOT NULL OR mobility_out IS NOT NULL
            GROUP BY departamento_code, municipio_code, epi_year, epi_week
        ),
        dept_week AS (
            SELECT departamento_code, epi_year, epi_week,
                   SUM(COALESCE(mobility_out, 0)) AS out_flow,
                   SUM(COALESCE(mobility_in, 0)) AS in_flow
            FROM muni_week
            GROUP BY departamento_code, epi_year, epi_week
        ),
        pairs AS (
            SELECT a.departamento_code AS origin,
                   b.departamento_code AS dest,
                   SUM(SQRT(GREATEST(a.out_flow, 0) * GREATEST(b.in_flow, 0))) AS passengers
            FROM dept_week a
            INNER JOIN dept_week b
              ON a.epi_year = b.epi_year AND a.epi_week = b.epi_week
             AND a.departamento_code <> b.departamento_code
            GROUP BY a.departamento_code, b.departamento_code
        )
        SELECT origin, dest, passengers
        FROM pairs
        WHERE passengers > 0
        ORDER BY passengers DESC
        LIMIT %s
    """
    try:
        with get_db_connection() as conn:
            rows = pd.read_sql(query, conn, params=(limit,))
        if rows.empty:
            return pd.DataFrame()
        agg = {
            (str(r["origin"]).zfill(2), str(r["dest"]).zfill(2)): float(r["passengers"])
            for _, r in rows.iterrows()
        }
        return _od_pairs_to_dataframe(agg, coords, limit)
    except Exception as exc:
        logger.warning("Supabase OD map query failed: %s", exc)
        return pd.DataFrame()


def _od_pairs_to_dataframe(
    agg: dict[tuple[str, str], float],
    coords: dict[str, tuple[float, float]],
    limit: int,
) -> pd.DataFrame:
    records = []
    for (origin, dest), passengers in agg.items():
        if origin not in coords or dest not in coords:
            continue
        origin_lat, origin_lon = coords[origin]
        dest_lat, dest_lon = coords[dest]
        records.append({
            "origin_code": origin,
            "dest_code": dest,
            "origin_lat": origin_lat,
            "origin_lon": origin_lon,
            "dest_lat": dest_lat,
            "dest_lon": dest_lon,
            "passengers": passengers,
        })
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    return df.sort_values("passengers", ascending=False).head(limit).reset_index(drop=True)


def get_mobility_od_map(limit: int = 200) -> pd.DataFrame:
    """Flujos OD por departamento: CSV nacional si existe; si no, proxy desde Supabase."""
    coords = _load_departamento_coords()
    if not coords:
        logger.error("No department coordinates (dim_departamentos lat/lon required for map)")
        return pd.DataFrame()

    if _MOBILITY_RAW.exists():
        df = _od_map_from_raw_csv(limit, coords)
        if not df.empty:
            return df

    if settings.resolved_database_url():
        return _od_map_from_supabase(limit, coords)

    return pd.DataFrame()
