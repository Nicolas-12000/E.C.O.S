"""Naive seasonal and Ridge baselines for the model ladder."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

MODELS_ROOT = Path(__file__).resolve().parent
DEFAULT_RIDGE_PATH = MODELS_ROOT / "ridge_model.joblib"


def _add_epi_weeks(epi_year: int, epi_week: int, delta: int) -> tuple[int, int]:
    week, year = epi_week + delta, epi_year
    while week > 52:
        week -= 52
        year += 1
    while week < 1:
        week += 52
        year -= 1
    return year, week


def naive_cases_for_week(
    df: pd.DataFrame,
    municipio_code: str,
    disease: str,
    target_year: int,
    target_week: int,
) -> float | None:
    """Same epidemiological week one calendar year earlier; no imputation."""
    prior_year = target_year - 1
    row = df[
        (df["municipio_code"] == municipio_code)
        & (df["disease"] == disease)
        & (df["epi_year"] == prior_year)
        & (df["epi_week"] == target_week)
    ]
    if row.empty:
        return None
    return float(row.iloc[0]["cases_total"])


def build_ridge_pipeline() -> Pipeline:
    numeric = ["epi_year", "epi_week", "cases_lag_1", "cases_lag_2", "cases_lag_4"]
    return Pipeline(
        steps=[
            (
                "prep",
                ColumnTransformer(
                    transformers=[
                        ("num", "passthrough", numeric),
                        ("disease", OneHotEncoder(handle_unknown="ignore"), ["disease"]),
                    ]
                ),
            ),
            ("model", Ridge(alpha=1.0, random_state=42)),
        ]
    )


def train_ridge_model(df: pd.DataFrame) -> Pipeline:
    from utils import add_lags

    work = add_lags(df)
    work = work.dropna(subset=["cases_total"])
    for col in ["cases_lag_1", "cases_lag_2", "cases_lag_4"]:
        work[col] = work[col].fillna(0.0)
    X = work[["epi_year", "epi_week", "cases_lag_1", "cases_lag_2", "cases_lag_4", "disease"]]
    y = work["cases_total"].astype(float)
    pipe = build_ridge_pipeline()
    pipe.fit(X, y)
    return pipe


def save_ridge_model(pipe: Pipeline, path: Path = DEFAULT_RIDGE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, path)


def load_ridge_model(path: Path = DEFAULT_RIDGE_PATH) -> Pipeline | None:
    if not path.exists():
        return None
    return joblib.load(path)


def ridge_predict_row(pipe: Pipeline, row: pd.Series, history: pd.DataFrame) -> float:
    payload = pd.DataFrame(
        [
            {
                "epi_year": int(row["epi_year"]),
                "epi_week": int(row["epi_week"]),
                "cases_lag_1": float(history["cases_total"].iloc[0]) if len(history) >= 1 else 0.0,
                "cases_lag_2": float(history["cases_total"].iloc[1]) if len(history) >= 2 else 0.0,
                "cases_lag_4": float(history["cases_total"].iloc[3]) if len(history) >= 4 else 0.0,
                "disease": row["disease"],
            }
        ]
    )
    pred = float(pipe.predict(payload)[0])
    return max(0.0, pred)


def week_start_date(target_year: int, target_week: int) -> dt.date | None:
    try:
        return dt.date.fromisocalendar(target_year, target_week, 1)
    except Exception:
        return None
