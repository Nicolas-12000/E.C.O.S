#!/usr/bin/env python3
"""Train naive/Ridge/hybrid comparison and write models/metrics.json with served model."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_ROOT = REPO_ROOT / "models"
if str(MODELS_ROOT) not in sys.path:
    sys.path.insert(0, str(MODELS_ROOT))

from baseline_forecast import naive_cases_for_week, save_ridge_model, train_ridge_model
from utils import add_lags, evaluate_metrics, load_dataset, split_train_test

DEFAULT_PARQUET = REPO_ROOT / "data/processed/curated_weekly_parquet"
DEFAULT_CSV = REPO_ROOT / "data/processed/curated_weekly_csv_fact_core_weekly"
METRICS_OUT = MODELS_ROOT / "metrics.json"


def dataset_fingerprint(df: pd.DataFrame) -> str:
    payload = f"{len(df)}|{df['week_start_date'].max()}|{df['cases_total'].sum()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def eval_naive(full_df: pd.DataFrame, test_df: pd.DataFrame) -> dict:
    preds = []
    actuals = []
    for _, row in test_df.iterrows():
        val = naive_cases_for_week(
            full_df,
            str(row["municipio_code"]),
            str(row["disease"]),
            int(row["epi_year"]),
            int(row["epi_week"]),
        )
        if val is None:
            continue
        preds.append(val)
        actuals.append(float(row["cases_total"]))
    if not actuals:
        return {"mae": float("inf"), "rmse": float("inf"), "r2": 0.0}
    y_true = np.array(actuals)
    y_pred = np.array(preds)
    return evaluate_metrics(y_true, y_pred, threshold=float(np.percentile(y_true, 90) if len(y_true) else 5))


def eval_ridge(pipe, test_df: pd.DataFrame) -> dict:
    from baseline_forecast import ridge_predict_row

    work = add_lags(test_df).sort_values(["municipio_code", "disease", "week_start_date"])
    preds = []
    actuals = []
    for _, row in work.iterrows():
        hist = work[
            (work["municipio_code"] == row["municipio_code"])
            & (work["disease"] == row["disease"])
            & (work["week_start_date"] < row["week_start_date"])
        ].sort_values("week_start_date", ascending=False)
        pred = ridge_predict_row(pipe, row, hist.reset_index(drop=True))
        preds.append(pred)
        actuals.append(float(row["cases_total"]))
    y_true = np.array(actuals)
    y_pred = np.array(preds)
    return evaluate_metrics(y_true, y_pred, threshold=float(np.percentile(y_true, 90)))


def load_hybrid_mae(metrics_path: Path) -> float | None:
    if not metrics_path.exists():
        return None
    data = json.loads(metrics_path.read_text())
    return data.get("mae")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Ridge baseline and select served model")
    parser.add_argument("--hybrid-metrics", default=str(MODELS_ROOT / "final_model_metrics.json"))
    args = parser.parse_args()

    df = load_dataset(DEFAULT_PARQUET, DEFAULT_CSV)
    df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
    df = df.dropna(subset=["week_start_date", "municipio_code", "disease"])

    train, test = split_train_test(df, 0.8)
    ridge = train_ridge_model(train)
    save_ridge_model(ridge)

    naive_metrics = eval_naive(df, test)
    ridge_metrics = eval_ridge(ridge, test)

    hybrid_metrics = {}
    hybrid_path = Path(args.hybrid_metrics)
    if hybrid_path.exists():
        hybrid_metrics = json.loads(hybrid_path.read_text())

    hybrid_mae = hybrid_metrics.get("mae")
    ridge_mae = ridge_metrics["mae"]
    if hybrid_mae is None or hybrid_mae > ridge_mae:
        served = "ridge"
    else:
        served = "hybrid"

    out = {
        "dataset_hash": dataset_fingerprint(df),
        "served_model": served,
        "naive": naive_metrics,
        "ridge": ridge_metrics,
        "hybrid": hybrid_metrics or None,
    }
    METRICS_OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[ok] served_model={served} written to {METRICS_OUT}")
    print(f"     naive MAE={naive_metrics['mae']:.4f} ridge MAE={ridge_mae:.4f} hybrid MAE={hybrid_mae}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
