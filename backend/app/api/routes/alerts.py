"""Alerts — forecast-first when a prediction run exists; otherwise observed historic slice."""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Query

from app.services.epidemiology import (
    VALID_DISEASES,
    OUTBREAK_THRESHOLD,
    _load_df,
    calculate_endemic_channel,
    classify_endemic_risk,
)
from app.services.model_registry import get_served_model_name
from app.services.prediction_store import fetch_run_alerts, get_latest_run

logger = logging.getLogger(__name__)
router = APIRouter()

STALE_AFTER_DAYS = 42  # ~6 epidemiological weeks


def _is_stale(as_of: date | None) -> bool:
    if as_of is None:
        return True
    return (date.today() - as_of) > timedelta(days=STALE_AFTER_DAYS)


def _observed_alerts(disease: str | None, limit: int) -> dict:
    try:
        df = _load_df()
    except FileNotFoundError:
        return {
            "mode": "unavailable",
            "alerts": [],
            "message": "No curated data available.",
        }

    latest_date = df["week_start_date"].max()
    recent = df[df["week_start_date"] == latest_date].copy()
    if disease:
        if disease not in VALID_DISEASES:
            return {"mode": "historic", "alerts": [], "message": f"disease must be one of {sorted(VALID_DISEASES)}"}
        recent = recent[recent["disease"] == disease]

    as_of_row = df.loc[df["week_start_date"] == latest_date].iloc[0]
    as_of_date = latest_date.date() if hasattr(latest_date, "date") else latest_date

    alert_list = []
    for _, row in recent.iterrows():
        cases = int(row["cases_total"])
        muni = str(row["municipio_code"])
        dis = str(row["disease"])
        epi_week = int(row["epi_week"])
        channel = calculate_endemic_channel(muni, dis, epi_week)
        threshold = channel.get("p90") or channel.get("p75") or OUTBREAK_THRESHOLD
        if cases < threshold:
            continue
        risk_level = classify_endemic_risk(cases, channel)
        alert_list.append({
            "municipio_code": muni,
            "municipio_name": None,
            "departamento_code": str(row.get("departamento_code", "")),
            "disease": dis,
            "epi_year": int(row["epi_year"]),
            "epi_week": epi_week,
            "cases_total": cases,
            "predicted_cases": None,
            "horizon_weeks": None,
            "outbreak_threshold": threshold,
            "risk_level": risk_level,
            "signals": {
                "trends_score": round(float(row.get("trends_score", 0) or 0), 2),
                "rss_mentions": int(float(row.get("rss_mentions", 0) or 0)),
                "signals_score": round(float(row.get("signals_score", 0) or 0), 3),
            },
        })
    alert_list = sorted(alert_list, key=lambda x: x["cases_total"], reverse=True)[:limit]

    stale = _is_stale(as_of_date)
    return {
        "mode": "historic",
        "is_stale": stale,
        "title": "Último corte del archivo (no es pronóstico)" if stale else "Casos observados en el último corte",
        "as_of_epi_year": int(as_of_row["epi_year"]),
        "as_of_epi_week": int(as_of_row["epi_week"]),
        "as_of_week_start_date": str(as_of_date),
        "alerts": alert_list,
        "total": len(alert_list),
        "latest_week": str(as_of_date),
        "outbreak_threshold": None,
        "threshold_mode": "endemic_p90",
        "disease_filter": disease,
    }


@router.get("/alerts", summary="Alertas por pronóstico o último corte observado")
def alerts(
    disease: str | None = Query(None, description="Filtrar por enfermedad (opcional)"),
    limit: int = Query(50, ge=1, le=200),
    horizon_weeks: int = Query(1, ge=1, le=4, description="Semanas adelante del run de pronóstico"),
):
    if disease and disease not in VALID_DISEASES:
        return {"alerts": [], "message": f"disease must be one of {sorted(VALID_DISEASES)}"}

    run = get_latest_run()
    if not run:
        return _observed_alerts(disease, limit)

    as_of_date = run["as_of_week_start_date"]
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.date()

    stale = _is_stale(as_of_date)
    served = get_served_model_name()
    try:
        rows = fetch_run_alerts(
            run["run_id"],
            disease=disease,
            horizon_weeks=horizon_weeks,
            model_family=served,
            limit=limit,
        )
    except Exception as exc:
        logger.warning("Forecast alerts query failed, falling back to historic: %s", exc)
        payload = _observed_alerts(disease, limit)
        payload["message"] = (
            "No se pudo leer prediction_points (¿aplicaste la migración 0003?). "
            f"Detalle: {exc}"
        )
        return payload

    alert_list = []
    for row in rows:
        alert_list.append({
            "municipio_code": row["municipio_code"],
            "municipio_name": row.get("municipio_name"),
            "departamento_code": row.get("departamento_code"),
            "disease": row["disease"],
            "epi_year": row["epi_year"],
            "epi_week": row["epi_week"],
            "cases_total": None,
            "predicted_cases": round(float(row["predicted_cases"]), 2),
            "horizon_weeks": row["horizon_weeks"],
            "outbreak_threshold": row.get("outbreak_threshold"),
            "risk_level": row.get("endemic_risk") or "moderate",
            "signals": None,
        })

    title = "Pronóstico de brote"
    if stale:
        title = f"Pronóstico (corte observado {as_of_date}; datos no recientes)"

    return {
        "mode": "forecast",
        "is_stale": stale,
        "title": title,
        "run_id": str(run["run_id"]),
        "model_name": run["model_name"],
        "served_model": served,
        "as_of_epi_year": run["as_of_epi_year"],
        "as_of_epi_week": run["as_of_epi_week"],
        "as_of_week_start_date": str(as_of_date),
        "horizon_weeks": horizon_weeks,
        "alerts": alert_list,
        "total": len(alert_list),
        "latest_week": str(as_of_date),
        "outbreak_threshold": None,
        "disease_filter": disease,
    }
