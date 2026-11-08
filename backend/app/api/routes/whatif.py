from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.epidemiology import (
    WhatIfRequest,
    WhatIfResponse,
    PredictionItem,
    WhatIfScenarioListResponse,
    WhatIfScenarioItem,
)
from app.services.epidemiology import VALID_DISEASES
from app.services.prediction_resolve import resolve_predictions
from app.services.whatif_store import list_scenarios, save_scenario

router = APIRouter()


def _lite_adjust_predictions(original: list[dict], adjustments: dict[str, float]) -> list[dict]:
    """Aproximación liviana en Render free (sin joblib). Solo didáctica."""
    factor = 1.0
    factor -= (adjustments.get("vaccination_coverage_pct") or 0) * 0.012
    factor += (adjustments.get("mobility_in") or 0) * 0.00015
    factor += (adjustments.get("mobility_out") or 0) * 0.00012
    factor += (adjustments.get("mobility_index") or 0) * 0.25
    factor += (adjustments.get("trends_score") or 0) * 0.008
    factor += (adjustments.get("rss_mentions") or 0) * 0.006
    factor += (adjustments.get("precipitation_mm") or 0) * 0.002
    factor += (adjustments.get("temp_avg_c") or 0) * 0.03
    factor = max(0.55, min(1.85, factor))
    adjusted: list[dict] = []
    for row in original:
        item = dict(row)
        item["predicted_cases"] = round(float(row["predicted_cases"]) * factor, 2)
        adjusted.append(item)
    return adjusted


@router.get("/whatif/scenarios", response_model=WhatIfScenarioListResponse, summary="Escenarios what-if guardados")
def whatif_scenarios(limit: int = Query(20, ge=1, le=100)):
    rows = list_scenarios(limit=limit)
    items = []
    for row in rows:
        created = row["created_at"]
        if hasattr(created, "isoformat"):
            created = created
        items.append(
            WhatIfScenarioItem(
                scenario_id=str(row["scenario_id"]),
                created_at=created,
                municipio_code=row["municipio_code"],
                disease=row["disease"],
                weeks_ahead=int(row["weeks_ahead"]),
                adjustments=dict(row["adjustments"] or {}),
                delta_total=row.get("delta_total"),
                notes=row.get("notes"),
            )
        )
    return WhatIfScenarioListResponse(scenarios=items, total=len(items))


@router.post("/whatif", response_model=WhatIfResponse, summary="Simulación What-if")
def what_if(req: WhatIfRequest):
    """
    Compara la predicción base con una predicción ajustada por variables exógenas
    (ej: aumento de vacunación, disminución de movilidad).
    """
    if req.disease not in VALID_DISEASES:
        raise HTTPException(status_code=422, detail=f"disease must be one of {sorted(VALID_DISEASES)}")

    has_adj = any(abs(v) > 1e-9 for v in (req.adjustments or {}).values())
    try:
        original, _ = resolve_predictions(req.municipio_code, req.disease, weeks_ahead=req.weeks_ahead)
        if has_adj and not settings.lite_production:
            adjusted, _ = resolve_predictions(
                req.municipio_code,
                req.disease,
                weeks_ahead=req.weeks_ahead,
                adjustments=req.adjustments,
            )
        elif has_adj and settings.lite_production:
            adjusted = _lite_adjust_predictions(original, req.adjustments)
        else:
            adjusted = original
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    total_orig = sum(p["predicted_cases"] for p in original)
    total_adj = sum(p["predicted_cases"] for p in adjusted)
    delta = round(total_adj - total_orig, 2)

    scenario_id = None
    if req.save_scenario:
        saved = save_scenario(
            req.municipio_code,
            req.disease,
            req.weeks_ahead,
            req.adjustments,
            delta,
            req.notes,
        )
        if saved:
            scenario_id = str(saved)

    return WhatIfResponse(
        original_predictions=[PredictionItem(**p) for p in original],
        adjusted_predictions=[PredictionItem(**p) for p in adjusted],
        delta_total=delta,
        scenario_id=scenario_id,
    )
