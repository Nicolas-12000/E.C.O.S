#!/usr/bin/env python3
"""Export cases-only gold layer (no exogenous wide features)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

CASE_COLS = [
    "epi_year",
    "epi_week",
    "week_start_date",
    "week_end_date",
    "departamento_code",
    "municipio_code",
    "event_code",
    "disease",
    "cases_total",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export gold cases parquet")
    parser.add_argument("--supabase", action="store_true")
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "data/processed/gold_cases_weekly.parquet"),
    )
    args = parser.parse_args()

    if args.supabase:
        db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
        if not db_url:
            print("[error] SUPABASE_DB_URL required")
            return 1
        cols = ", ".join(CASE_COLS)
        with psycopg.connect(db_url) as conn:
            df = pd.read_sql(f"SELECT {cols} FROM public.fact_core_weekly", conn)
    else:
        src = REPO_ROOT / "data/processed/curated_weekly_parquet"
        if not src.exists():
            print(f"[error] missing {src}")
            return 1
        df = pd.read_parquet(src)
        df = df[[c for c in CASE_COLS if c in df.columns]]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"[ok] gold cases -> {out} ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
