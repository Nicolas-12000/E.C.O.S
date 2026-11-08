"""Pronóstico en prod free: Supabase (prediction_points) antes que joblib en RAM."""

from __future__ import annotations

from datetime import date

from app.core.config import settings
from app.services.model_registry import get_served_model_name
from app.services.prediction_store import get_latest_run, fetch_municipio_points


def _points_to_api(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        wsd = row.get("week_start_date")
        if hasattr(wsd, "date"):
            wsd = wsd.date()
        out.append(
            {
                "epi_year": int(row["epi_year"]),
                "epi_week": int(row["epi_week"]),
                "week_start_date": wsd if isinstance(wsd, date) else wsd,
                "disease": row["disease"],
                "municipio_code": row["municipio_code"],
                "departamento_code": row.get("departamento_code") or "",
                "predicted_cases": float(row["predicted_cases"]),
                "outbreak_flag": bool(row.get("outbreak_flag")),
                "outbreak_threshold": float(row.get("outbreak_threshold") or 0),
                "endemic_risk": row.get("endemic_risk"),
                "shap_values": None,
                "horizon_weeks": int(row.get("horizon_weeks", 0)),
                "model_family": row.get("model_family"),
            }
        )
    return out


def resolve_predictions(
    municipio_code: str,
    disease: str,
    weeks_ahead: int = 2,
    adjustments: dict[str, float] | None = None,
) -> tuple[list[dict], str]:
    """
    Returns (predictions, source) where source is 'supabase' | 'model'.
    """
    if adjustments and settings.lite_production:
        raise ValueError(
            "La simulación what-if con sliders requiere ECOS_FULL_API=true (plan con más RAM) "
            "o ejecutar el API en local con modelos joblib."
        )

    served = get_served_model_name()
    stored = fetch_municipio_points(
        municipio_code,
        disease,
        weeks_ahead=weeks_ahead,
        model_family=served,
    )
    if stored and not adjustments:
        return _points_to_api(stored), "supabase"

    if settings.lite_production:
        if stored:
            return _points_to_api(stored), "supabase"
        raise ValueError(
            "No hay puntos de pronóstico en Supabase para ese municipio. "
            "Corre weekly_forecast_job.py contra tu base y vuelve a desplegar."
        )

    from app.services.prediction import predict_cases

    if not get_latest_run() and not adjustments:
        raise ValueError("No prediction run in database and ML model unavailable")
    return predict_cases(
        municipio_code,
        disease,
        weeks_ahead=weeks_ahead,
        adjustments=adjustments,
    ), "model"
