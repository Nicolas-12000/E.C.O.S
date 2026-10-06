from fastapi import APIRouter, HTTPException, Query

from app.schemas.epidemiology import (
    WhatIfRequest,
    WhatIfResponse,
    PredictionItem,
    WhatIfScenarioListResponse,
    WhatIfScenarioItem,
)
from app.services.prediction import predict_cases
from app.services.epidemiology import VALID_DISEASES
from app.services.whatif_store import list_scenarios, save_scenario

router = APIRouter()


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

    try:
        original = predict_cases(req.municipio_code, req.disease, weeks_ahead=req.weeks_ahead)
        adjusted = predict_cases(
            req.municipio_code,
            req.disease,
            weeks_ahead=req.weeks_ahead,
            adjustments=req.adjustments,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

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
