import datetime
import logging
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.services.epidemiology import (
    OUTBREAK_THRESHOLD,
    VALID_DISEASES,
    _load_df,
    calculate_endemic_channel,
    classify_endemic_risk,
    get_history,
    get_last_known_features,
)
from app.services.model_registry import get_served_model_name

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "models") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "models"))

from baseline_forecast import (
    load_ridge_model,
    naive_cases_for_week,
    ridge_predict_row,
    week_start_date as iso_week_start,
)
from models.hybrid_model import EcosHybridModel

logger = logging.getLogger(__name__)

MODEL_PATH_FINAL = REPO_ROOT / "models/final_model.joblib"

CLIMATE_COLS = [
    "temp_avg_c",
    "temp_min_c",
    "temp_max_c",
    "precipitation_mm",
    "temp_avg_c_actual",
    "temp_min_c_actual",
    "temp_max_c_actual",
    "precipitation_mm_actual",
]
EXOG_COLS = [
    "vaccination_coverage_pct",
    "rips_visits_total",
    "mobility_in",
    "mobility_out",
    "mobility_index",
    "trends_score",
    "rss_mentions",
    "signals_score",
]


@lru_cache(maxsize=1)
def load_hybrid_model():
    if MODEL_PATH_FINAL.exists():
        logger.info("Loading hybrid prediction model from %s", MODEL_PATH_FINAL)
        try:
            return EcosHybridModel(MODEL_PATH_FINAL)
        except Exception as e:
            logger.error("Failed to load hybrid model: %s", e)
            return None
    return None


def _add_epi_weeks(epi_year: int, epi_week: int, delta: int) -> tuple[int, int]:
    week = epi_week + delta
    year = epi_year
    while week > 52:
        week -= 52
        year += 1
    while week < 1:
        week += 52
        year -= 1
    return year, week


def _build_input_row(
    anchor_row: pd.Series,
    history: pd.DataFrame,
    horizon: int,
    adjustments: dict[str, float] | None = None,
) -> pd.DataFrame:
    anchor_year = int(anchor_row["epi_year"])
    anchor_week = int(anchor_row["epi_week"])
    target_year, target_week = _add_epi_weeks(anchor_year, anchor_week, horizon)

    numeric = {
        "epi_year": target_year,
        "epi_week": target_week,
        "cases_lag_1": float(history["cases_total"].iloc[0]) if len(history) >= 1 else 0.0,
        "cases_lag_2": float(history["cases_total"].iloc[1]) if len(history) >= 2 else 0.0,
        "cases_lag_4": float(history["cases_total"].iloc[3]) if len(history) >= 4 else 0.0,
    }
    for col in CLIMATE_COLS + EXOG_COLS:
        val = float(anchor_row[col]) if col in anchor_row.index and pd.notna(anchor_row[col]) else 0.0
        if adjustments and col in adjustments:
            val += adjustments[col]
        numeric[col] = val
    return pd.DataFrame([numeric])


def _append_prediction(
    predictions: list[dict],
    *,
    municipio_code: str,
    disease: str,
    last_row: pd.Series,
    target_year: int,
    target_week: int,
    predicted: float,
    horizon: int,
    shap_values: dict | None = None,
    model_family: str,
) -> None:
    week_start = iso_week_start(target_year, target_week)
    channel = calculate_endemic_channel(municipio_code, disease, target_week)
    risk_level = classify_endemic_risk(predicted, channel)
    threshold = channel.get("p90") or channel.get("p75") or OUTBREAK_THRESHOLD
    predictions.append(
        {
            "epi_year": target_year,
            "epi_week": target_week,
            "week_start_date": week_start,
            "disease": disease,
            "municipio_code": municipio_code,
            "departamento_code": str(last_row.get("departamento_code", "")),
            "predicted_cases": round(predicted, 2),
            "outbreak_flag": predicted >= threshold,
            "outbreak_threshold": threshold,
            "endemic_risk": risk_level,
            "shap_values": shap_values,
            "horizon_weeks": horizon,
            "model_family": model_family,
        }
    )


def predict_cases_hybrid(
    municipio_code: str,
    disease: str,
    weeks_ahead: int = 2,
    adjustments: dict[str, float] | None = None,
) -> list[dict]:
    hybrid = load_hybrid_model()
    if hybrid is None:
        raise FileNotFoundError("Hybrid model not available. Run the training pipeline first.")

    last_row = get_last_known_features(municipio_code, disease)
    if last_row is None:
        raise FileNotFoundError(f"No historical data for municipio_code={municipio_code} disease={disease}")

    history = get_history(municipio_code, disease, limit=10).sort_values(
        "week_start_date", ascending=False
    ).reset_index(drop=True)
    anchor_year, anchor_week = int(last_row["epi_year"]), int(last_row["epi_week"])
    predictions: list[dict] = []

    for horizon in range(1, weeks_ahead + 1):
        target_year, target_week = _add_epi_weeks(anchor_year, anchor_week, horizon)
        X_row = _build_input_row(last_row, history, horizon, adjustments=adjustments)
        residual_pred, shap_values = hybrid.predict_residual(X_row)

        prophet_pred = None
        week_start = iso_week_start(target_year, target_week)
        if week_start:
            prophet_pred = hybrid.get_prophet_baseline(
                municipio_code, disease, pd.Timestamp(week_start)
            )

        if prophet_pred is None:
            predicted = max(0.0, residual_pred)
        else:
            predicted = max(0.0, prophet_pred + residual_pred)

        _append_prediction(
            predictions,
            municipio_code=municipio_code,
            disease=disease,
            last_row=last_row,
            target_year=target_year,
            target_week=target_week,
            predicted=predicted,
            horizon=horizon,
            shap_values=shap_values,
            model_family="hybrid",
        )
    return predictions


def predict_cases_ridge(municipio_code: str, disease: str, weeks_ahead: int = 2) -> list[dict]:
    pipe = load_ridge_model()
    if pipe is None:
        raise FileNotFoundError("Ridge model not found. Run scripts/train_model_ladder.py")

    last_row = get_last_known_features(municipio_code, disease)
    if last_row is None:
        raise FileNotFoundError(f"No historical data for municipio_code={municipio_code} disease={disease}")

    history = get_history(municipio_code, disease, limit=10).sort_values(
        "week_start_date", ascending=False
    ).reset_index(drop=True)
    anchor_year, anchor_week = int(last_row["epi_year"]), int(last_row["epi_week"])
    predictions: list[dict] = []

    for horizon in range(1, weeks_ahead + 1):
        target_year, target_week = _add_epi_weeks(anchor_year, anchor_week, horizon)
        row = last_row.copy()
        row["epi_year"] = target_year
        row["epi_week"] = target_week
        row["disease"] = disease
        predicted = ridge_predict_row(pipe, row, history)
        _append_prediction(
            predictions,
            municipio_code=municipio_code,
            disease=disease,
            last_row=last_row,
            target_year=target_year,
            target_week=target_week,
            predicted=predicted,
            horizon=horizon,
            model_family="ridge",
        )
    return predictions


def predict_cases_naive(municipio_code: str, disease: str, weeks_ahead: int = 2) -> list[dict]:
    df = _load_df()
    last_row = get_last_known_features(municipio_code, disease)
    if last_row is None:
        raise FileNotFoundError(f"No historical data for municipio_code={municipio_code} disease={disease}")

    anchor_year, anchor_week = int(last_row["epi_year"]), int(last_row["epi_week"])
    predictions: list[dict] = []

    for horizon in range(1, weeks_ahead + 1):
        target_year, target_week = _add_epi_weeks(anchor_year, anchor_week, horizon)
        naive = naive_cases_for_week(df, municipio_code, disease, target_year, target_week)
        if naive is None:
            continue
        _append_prediction(
            predictions,
            municipio_code=municipio_code,
            disease=disease,
            last_row=last_row,
            target_year=target_year,
            target_week=target_week,
            predicted=naive,
            horizon=horizon,
            model_family="naive",
        )
    if not predictions:
        raise FileNotFoundError("Naive forecast unavailable (no prior-year week)")
    return predictions


def predict_cases(
    municipio_code: str,
    disease: str,
    weeks_ahead: int = 2,
    adjustments: dict[str, float] | None = None,
    model_family: str | None = None,
) -> list[dict]:
    if disease not in VALID_DISEASES:
        raise ValueError(f"disease must be one of {sorted(VALID_DISEASES)}")
    if not (1 <= weeks_ahead <= 4):
        raise ValueError("weeks_ahead must be between 1 and 4")

    family = model_family or get_served_model_name()
    if family == "naive":
        return predict_cases_naive(municipio_code, disease, weeks_ahead=weeks_ahead)
    if family == "ridge":
        return predict_cases_ridge(municipio_code, disease, weeks_ahead=weeks_ahead)
    return predict_cases_hybrid(
        municipio_code, disease, weeks_ahead=weeks_ahead, adjustments=adjustments
    )
