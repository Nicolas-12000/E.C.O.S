"""Reads models/metrics.json to choose the production forecaster."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
METRICS_PATH = REPO_ROOT / "models" / "metrics.json"


@lru_cache(maxsize=1)
def get_served_model_name() -> str:
    if not METRICS_PATH.exists():
        return "hybrid"
    try:
        data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        name = data.get("served_model", "hybrid")
        if name in {"naive", "ridge", "hybrid"}:
            return name
    except Exception as exc:
        logger.warning("Could not read metrics.json: %s", exc)
    return "hybrid"


def reload_registry() -> None:
    get_served_model_name.cache_clear()
