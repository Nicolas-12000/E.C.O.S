#!/usr/bin/env python3
"""Validate gold dataset contract: unique keys and non-negative cases."""

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

KEY_COLS = ["epi_year", "epi_week", "municipio_code", "disease"]


def load_from_files() -> pd.DataFrame:
    for path in [
        REPO_ROOT / "data/processed/curated_weekly_fresh_parquet",
        REPO_ROOT / "data/processed/curated_weekly_parquet",
    ]:
        if path.exists():
            return pd.read_parquet(path)
    csv_dir = REPO_ROOT / "data/processed/curated_weekly_csv_fact_core_weekly"
    if csv_dir.exists():
        files = sorted(csv_dir.glob("*.csv"))
        if files:
            return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    raise FileNotFoundError("No local gold dataset found")


def load_from_supabase(db_url: str) -> pd.DataFrame:
    with psycopg.connect(db_url) as conn:
        return pd.read_sql("SELECT * FROM public.fact_core_weekly", conn)


def validate(df: pd.DataFrame) -> int:
    missing = [c for c in KEY_COLS + ["cases_total"] if c not in df.columns]
    if missing:
        print(f"[error] missing columns: {missing}")
        return 1

    dup = df.duplicated(KEY_COLS, keep=False)
    dup_count = int(dup.sum())
    if dup_count:
        print(f"[error] duplicate primary keys: {dup_count} rows")
        return 1

    negative = int((pd.to_numeric(df["cases_total"], errors="coerce") < 0).sum())
    if negative:
        print(f"[error] negative cases_total: {negative}")
        return 1

    print(f"[ok] contract valid ({len(df)} rows, keys unique, cases >= 0)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate fact_core_weekly contract")
    parser.add_argument("--supabase", action="store_true", help="Read from Supabase instead of local files")
    args = parser.parse_args()

    try:
        if args.supabase:
            db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
            if not db_url:
                print("[error] SUPABASE_DB_URL not set")
                return 1
            df = load_from_supabase(db_url)
            print("[info] loaded from Supabase fact_core_weekly")
        else:
            df = load_from_files()
            print("[info] loaded from local processed files")
    except Exception as exc:
        print(f"[error] load failed: {exc}")
        return 1

    return validate(df)


if __name__ == "__main__":
    raise SystemExit(main())
