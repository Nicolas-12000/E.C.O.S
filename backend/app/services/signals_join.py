"""Join department-grain signals onto municipio-level frames without cloning in gold."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
TRENDS_GLOB = "curated_weekly_csv_silver_signals_trends_dept"
RSS_GLOB = "curated_weekly_csv_silver_signals_rss_dept"
LEGACY_TRENDS = REPO_ROOT / "data/processed/signals_trends.csv"
LEGACY_RSS = REPO_ROOT / "data/processed/signals_rss.csv"


def _read_csv_dir(prefix: Path) -> pd.DataFrame | None:
    if not prefix.exists():
        return None
    files = sorted(prefix.glob("*.csv"))
    if not files:
        return None
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def _load_silver_trends() -> pd.DataFrame | None:
    for base in [REPO_ROOT / "data/processed", REPO_ROOT / "data/demo"]:
        df = _read_csv_dir(base / TRENDS_GLOB)
        if df is not None:
            return df
    if LEGACY_TRENDS.exists():
        return pd.read_csv(LEGACY_TRENDS)
    return None


def _load_silver_rss() -> pd.DataFrame | None:
    for base in [REPO_ROOT / "data/processed", REPO_ROOT / "data/demo"]:
        df = _read_csv_dir(base / RSS_GLOB)
        if df is not None:
            return df
    if LEGACY_RSS.exists():
        return pd.read_csv(LEGACY_RSS)
    return None


def attach_department_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Left-join dept signals for alert/API use when gold omits embedded scores."""
    if df.empty:
        return df
    if "trends_score" in df.columns and df["trends_score"].notna().any():
        return df

    out = df.copy()
    trends = _load_silver_trends()
    rss = _load_silver_rss()
    join_keys = ["departamento_code", "epi_year", "epi_week", "disease"]

    if trends is not None and "departamento_code" in trends.columns:
        tcols = [c for c in join_keys + ["trends_score"] if c in trends.columns]
        out = out.merge(trends[tcols].drop_duplicates(join_keys), on=join_keys, how="left", suffixes=("", "_t"))

    if rss is not None and "departamento_code" in rss.columns:
        rcols = [c for c in join_keys + ["rss_mentions"] if c in rss.columns]
        out = out.merge(rss[rcols].drop_duplicates(join_keys), on=join_keys, how="left", suffixes=("", "_r"))

    trends = out["trends_score"] if "trends_score" in out.columns else None
    rss = out["rss_mentions"] if "rss_mentions" in out.columns else None
    if trends is not None or rss is not None:
        t = trends.fillna(0) if trends is not None else 0.0
        r = rss.fillna(0) if rss is not None else 0.0
        both_missing = (
            (trends.isna() & rss.isna())
            if trends is not None and rss is not None
            else (trends.isna() if trends is not None else rss.isna())
        )
        out["signals_score"] = np.where(both_missing, np.nan, t * 0.7 + r * 0.3)
    return out
