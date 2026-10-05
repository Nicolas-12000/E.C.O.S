#!/usr/bin/env python3
"""Weekly operational forecast: refresh signals (optional), score model, persist run in Supabase."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(REPO_ROOT / ".env")

from app.services.epidemiology import get_data_as_of, reload_curated_cache, VALID_DISEASES
from app.services.prediction import predict_cases
from app.services.prediction_store import (
    create_run,
    get_latest_run,
    insert_points,
    sync_legacy_predictions_table,
)


def run_step(name: str, cmd: list[str]) -> bool:
    print(f"\n== {name} ==")
    print(" ".join(cmd))
    try:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[error] {name} failed: {exc.returncode}")
        return False


def load_targets_from_supabase(db_url: str, limit: int | None) -> list[tuple[str, str]]:
    diseases = sorted(VALID_DISEASES)
    placeholders = ", ".join(["%s"] * len(diseases))
    query = f"""
        SELECT municipio_code, disease, COUNT(*) AS n
        FROM public.fact_core_weekly
        WHERE disease IN ({placeholders})
        GROUP BY municipio_code, disease
        HAVING COUNT(*) >= 8
        ORDER BY SUM(cases_total) DESC
    """
    with psycopg.connect(db_url) as conn:
        df = pd.read_sql(query, conn, params=diseases)
    if limit:
        df = df.head(limit)
    return list(df[["municipio_code", "disease"]].itertuples(index=False, name=None))


def main() -> int:
    parser = argparse.ArgumentParser(description="ECOS weekly forecast job")
    parser.add_argument("--skip-signals", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--limit", type=int, default=200, help="Max municipio/disease pairs to score")
    parser.add_argument("--weeks-ahead", type=int, default=4)
    parser.add_argument("--model-name", default="hybrid_v1")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("[error] SUPABASE_DB_URL required")
        return 1

    python = sys.executable

    if not args.skip_validate:
        if not run_step(
            "Validate gold contract",
            [python, str(SCRIPTS_DIR / "validate_gold_contract.py"), "--supabase"],
        ):
            return 1

    if not args.skip_signals:
        run_step("Fetch signals", [python, str(SCRIPTS_DIR / "fetch_signals.py")])

    reload_curated_cache()
    as_of = get_data_as_of()
    if not as_of:
        print("[error] could not determine as_of from fact_core_weekly")
        return 1

    print(f"[info] anchor week S{as_of['epi_week']} {as_of['epi_year']} ({as_of['week_start_date']})")

    targets = load_targets_from_supabase(db_url, args.limit)
    if not targets:
        print("[error] no targets in Supabase")
        return 1

    run_id = create_run(
        model_name=args.model_name,
        as_of_epi_year=as_of["epi_year"],
        as_of_epi_week=as_of["epi_week"],
        as_of_week_start_date=as_of["week_start_date"],
        notes=args.notes or f"weekly job {time.strftime('%Y-%m-%d')}",
    )
    print(f"[info] run_id={run_id}")

    all_points: list[dict] = []
    for municipio_code, disease in targets:
        try:
            preds = predict_cases(municipio_code, disease, weeks_ahead=args.weeks_ahead)
        except Exception as exc:
            print(f"[warn] skip {municipio_code}/{disease}: {exc}")
            continue
        all_points.extend(preds)

    if not all_points:
        print("[error] no predictions generated")
        return 1

    inserted = insert_points(run_id, all_points)
    sync_legacy_predictions_table(run_id, horizon_weeks=1)
    print(f"[ok] stored {inserted} prediction points (run {run_id})")
    prev = get_latest_run()
    if prev:
        print(f"[ok] latest run model={prev.get('model_name')} as_of={prev.get('as_of_week_start_date')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
