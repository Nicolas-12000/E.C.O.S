"""Persist and read weekly forecast runs in Supabase."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime
from typing import Any

from psycopg.rows import dict_row

from app.core.db import get_db_connection

logger = logging.getLogger(__name__)


def _top_shap(shap_values: dict[str, float] | None, n: int = 3) -> dict[str, float] | None:
    if not shap_values:
        return None
    items = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)[:n]
    return {k: v for k, v in items}


def get_latest_run() -> dict[str, Any] | None:
    query = """
        SELECT run_id, model_name, as_of_epi_year, as_of_epi_week,
               as_of_week_start_date, created_at, notes
        FROM public.prediction_runs
        ORDER BY created_at DESC
        LIMIT 1
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                row = cur.fetchone()
                if not row:
                    return None
                return dict(row)
    except Exception as exc:
        logger.warning("prediction_runs unavailable: %s", exc)
        return None


def create_run(
    model_name: str,
    as_of_epi_year: int,
    as_of_epi_week: int,
    as_of_week_start_date: date,
    notes: str | None = None,
) -> uuid.UUID:
    run_id = uuid.uuid4()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.prediction_runs (
                    run_id, model_name, as_of_epi_year, as_of_epi_week,
                    as_of_week_start_date, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    model_name,
                    as_of_epi_year,
                    as_of_epi_week,
                    as_of_week_start_date,
                    notes,
                ),
            )
        conn.commit()
    return run_id


def insert_points(run_id: uuid.UUID, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    sql = """
        INSERT INTO public.prediction_points (
            run_id, municipio_code, departamento_code, disease, horizon_weeks,
            model_family, epi_year, epi_week, week_start_date, predicted_cases,
            outbreak_flag, outbreak_threshold, endemic_risk, shap_top_factors
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (run_id, municipio_code, disease, horizon_weeks, model_family)
        DO UPDATE SET
            predicted_cases = EXCLUDED.predicted_cases,
            outbreak_flag = EXCLUDED.outbreak_flag,
            outbreak_threshold = EXCLUDED.outbreak_threshold,
            endemic_risk = EXCLUDED.endemic_risk,
            shap_top_factors = EXCLUDED.shap_top_factors,
            week_start_date = EXCLUDED.week_start_date,
            epi_year = EXCLUDED.epi_year,
            epi_week = EXCLUDED.epi_week
    """
    count = 0
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for row in rows:
                shap_payload = _top_shap(row.get("shap_values"))
                cur.execute(
                    sql,
                    (
                        run_id,
                        row["municipio_code"],
                        row.get("departamento_code"),
                        row["disease"],
                        int(row["horizon_weeks"]),
                        row.get("model_family", "hybrid"),
                        int(row["epi_year"]),
                        int(row["epi_week"]),
                        row.get("week_start_date"),
                        float(row["predicted_cases"]),
                        bool(row.get("outbreak_flag")),
                        row.get("outbreak_threshold"),
                        row.get("endemic_risk"),
                        json.dumps(shap_payload) if shap_payload else None,
                    ),
                )
                count += 1
        conn.commit()
    return count


def fetch_run_alerts(
    run_id: uuid.UUID,
    disease: str | None = None,
    horizon_weeks: int = 1,
    model_family: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    filters = ["p.run_id = %s", "p.horizon_weeks = %s", "p.outbreak_flag = TRUE"]
    params: list[Any] = [run_id, horizon_weeks]
    if model_family:
        filters.append("p.model_family = %s")
        params.append(model_family)
    if disease:
        filters.append("p.disease = %s")
        params.append(disease)
    params.append(limit)
    query = f"""
        SELECT
            p.municipio_code,
            p.departamento_code,
            m.municipio_name,
            p.disease,
            p.epi_year,
            p.epi_week,
            p.week_start_date,
            p.predicted_cases,
            p.outbreak_threshold,
            p.endemic_risk,
            p.horizon_weeks
        FROM public.prediction_points p
        LEFT JOIN public.dim_municipios m ON m.municipio_code = p.municipio_code
        WHERE {" AND ".join(filters)}
        ORDER BY p.predicted_cases DESC
        LIMIT %s
    """
    with get_db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, tuple(params))
            return [dict(r) for r in cur.fetchall()]


def sync_legacy_predictions_table(
    run_id: uuid.UUID, horizon_weeks: int = 1, model_family: str = "hybrid"
) -> None:
    """Mirror horizon-1 points into public.predictions for chat/RAG compatibility."""
    query = """
        SELECT municipio_code, departamento_code, disease, epi_year, epi_week,
               week_start_date, predicted_cases, outbreak_flag, outbreak_threshold,
               endemic_risk, shap_top_factors
        FROM public.prediction_points
        WHERE run_id = %s AND horizon_weeks = %s AND model_family = %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (run_id, horizon_weeks, model_family))
                rows = cur.fetchall()
                if not rows:
                    return
                cur.execute(
                    "DELETE FROM public.predictions WHERE created_at < NOW() - INTERVAL '1 year'"
                )
                for row in rows:
                    cur.execute(
                        """
                        INSERT INTO public.predictions (
                            departamento_code, municipio_code, disease,
                            epi_year, epi_week, week_start_date,
                            predicted_cases, outbreak_flag, outbreak_threshold,
                            endemic_risk, shap_top_factors
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            row["departamento_code"],
                            row["municipio_code"],
                            row["disease"],
                            row["epi_year"],
                            row["epi_week"],
                            row["week_start_date"],
                            row["predicted_cases"],
                            row["outbreak_flag"],
                            row["outbreak_threshold"],
                            row["endemic_risk"],
                            json.dumps(row["shap_top_factors"])
                            if row["shap_top_factors"]
                            else None,
                        ),
                    )
            conn.commit()
    except Exception as exc:
        logger.warning("Could not sync legacy predictions table: %s", exc)
