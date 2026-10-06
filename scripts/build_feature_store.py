#!/usr/bin/env python3
"""Build ML feature store: gold cases/exog + silver signals joined at department grain."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = REPO_ROOT / "data/processed/curated_weekly_parquet"
DEFAULT_OUT = REPO_ROOT / "data/processed/feature_store_weekly.parquet"


def _read_csv_dir(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    files = sorted(path.glob("*.csv"))
    if not files:
        return None
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def load_gold(path: Path) -> pd.DataFrame:
    if path.is_dir() or path.suffix == ".parquet":
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        cases_dir = REPO_ROOT / "data/processed/curated_weekly_csv_fact_cases_weekly"
        if cases_dir.exists():
            df = _read_csv_dir(cases_dir)
            if df is not None:
                wide = _read_csv_dir(REPO_ROOT / "data/processed/curated_weekly_csv_fact_core_weekly")
                if wide is not None:
                    keys = ["epi_year", "epi_week", "municipio_code", "disease"]
                    exog = [c for c in wide.columns if c not in df.columns or c in keys]
                    return wide.drop_duplicates(keys)
                return df
        return pd.read_parquet(path)
    return pd.read_parquet(path)


def join_signals(df: pd.DataFrame, prefix: Path) -> pd.DataFrame:
    join_keys = ["departamento_code", "epi_year", "epi_week", "disease"]
    out = df.copy()
    trends = _read_csv_dir(prefix.parent / f"{prefix.name}_silver_signals_trends_dept")
    if trends is None:
        legacy = REPO_ROOT / "data/processed/signals_trends.csv"
        if legacy.exists():
            trends = pd.read_csv(legacy)
    rss = _read_csv_dir(prefix.parent / f"{prefix.name}_silver_signals_rss_dept")
    if rss is None:
        legacy = REPO_ROOT / "data/processed/signals_rss.csv"
        if legacy.exists():
            rss = pd.read_csv(legacy)

    if trends is not None and "departamento_code" in trends.columns:
        tcols = [c for c in join_keys + ["trends_score"] if c in trends.columns]
        out = out.merge(trends[tcols].drop_duplicates(join_keys), on=join_keys, how="left")
    if rss is not None and "departamento_code" in rss.columns:
        rcols = [c for c in join_keys + ["rss_mentions"] if c in rss.columns]
        out = out.merge(rss[rcols].drop_duplicates(join_keys), on=join_keys, how="left")

    if "trends_score" in out.columns or "rss_mentions" in out.columns:
        out["signals_score"] = np.where(
            out["trends_score"].isna() & out["rss_mentions"].isna()
            if "trends_score" in out.columns and "rss_mentions" in out.columns
            else False,
            np.nan,
            out.get("trends_score", pd.Series(0, index=out.index)).fillna(0) * 0.7
            + out.get("rss_mentions", pd.Series(0, index=out.index)).fillna(0) * 0.3,
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build feature_store_weekly.parquet")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD))
    parser.add_argument("--csv-prefix", default=str(REPO_ROOT / "data/processed/curated_weekly_csv"))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    gold_path = Path(args.gold)
    if not gold_path.exists():
        print(f"[error] missing gold at {gold_path}")
        return 1

    df = load_gold(gold_path)
    df["week_start_date"] = pd.to_datetime(df["week_start_date"], errors="coerce")
    prefix = Path(args.csv_prefix)
    df = join_signals(df, prefix)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"[ok] feature store -> {out} ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
