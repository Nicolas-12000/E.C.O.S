"""Persist what-if scenario runs in Supabase."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from psycopg.rows import dict_row

from app.core.db import get_db_connection

logger = logging.getLogger(__name__)


def save_scenario(
    municipio_code: str,
    disease: str,
    weeks_ahead: int,
    adjustments: dict[str, float],
    delta_total: float,
    notes: str | None = None,
) -> uuid.UUID | None:
    scenario_id = uuid.uuid4()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.whatif_scenarios (
                        scenario_id, municipio_code, disease, weeks_ahead,
                        adjustments, delta_total, notes
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        scenario_id,
                        municipio_code,
                        disease,
                        weeks_ahead,
                        json.dumps(adjustments),
                        delta_total,
                        notes,
                    ),
                )
            conn.commit()
        return scenario_id
    except Exception as exc:
        logger.warning("whatif_scenarios unavailable: %s", exc)
        return None


def list_scenarios(limit: int = 20) -> list[dict[str, Any]]:
    query = """
        SELECT scenario_id, created_at, municipio_code, disease, weeks_ahead,
               adjustments, delta_total, notes
        FROM public.whatif_scenarios
        ORDER BY created_at DESC
        LIMIT %s
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("whatif_scenarios list failed: %s", exc)
        return []
