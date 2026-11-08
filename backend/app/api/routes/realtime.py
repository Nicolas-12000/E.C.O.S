"""WebSocket fan-out ligero: resumen de alertas sin bloquear el hilo HTTP."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.routes.alerts import alerts as alerts_http
from app.services.epidemiology import VALID_DISEASES

logger = logging.getLogger(__name__)
router = APIRouter()

PUSH_INTERVAL_S = 25


def _alerts_snapshot(disease: str | None, horizon_weeks: int, limit: int) -> dict:
    """Reusa la misma lógica que GET /alerts (sin duplicar SQL)."""
    payload = alerts_http(disease=disease, limit=limit, horizon_weeks=horizon_weeks)
    critical = sum(1 for a in payload.get("alerts", []) if a.get("risk_level") == "critical")
    high = sum(1 for a in payload.get("alerts", []) if a.get("risk_level") == "high")
    return {
        "type": "alerts_tick",
        "mode": payload.get("mode"),
        "total": payload.get("total", 0),
        "critical": critical,
        "high": high,
        "is_stale": payload.get("is_stale", False),
        "as_of_week_start_date": payload.get("as_of_week_start_date"),
        "horizon_weeks": horizon_weeks,
        "disease_filter": disease,
    }


@router.websocket("/ws/alerts")
async def ws_alerts(
    websocket: WebSocket,
    disease: str | None = Query(None),
    horizon_weeks: int = Query(1, ge=1, le=4),
    limit: int = Query(50, ge=1, le=200),
):
    if disease and disease not in VALID_DISEASES:
        await websocket.close(code=4400)
        return

    await websocket.accept()
    logger.info("WS alerts connected disease=%s horizon=%s", disease, horizon_weeks)
    try:
        while True:
            snap = await asyncio.to_thread(_alerts_snapshot, disease, horizon_weeks, limit)
            await websocket.send_json(snap)
            await asyncio.sleep(PUSH_INTERVAL_S)
    except WebSocketDisconnect:
        logger.info("WS alerts disconnected")
    except Exception as exc:
        logger.warning("WS alerts error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
