#!/usr/bin/env python3
"""Run the weekly forecast job (Supabase prediction_runs).

Legacy CSV output is optional export only; operational source is prediction_points.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="ECOS forecast (delegates to weekly_forecast_job)")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--weeks-ahead", type=int, default=4)
    parser.add_argument("--skip-signals", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument(
        "--export-csv",
        help="Optional path to export served-model horizon-1 rows after the job",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "weekly_forecast_job.py"),
        "--limit",
        str(args.limit),
        "--weeks-ahead",
        str(args.weeks_ahead),
    ]
    if args.skip_signals:
        cmd.append("--skip-signals")
    if args.skip_validate:
        cmd.append("--skip-validate")

    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        return result.returncode

    if args.export_csv:
        print("[info] CSV export not implemented; query prediction_points in Supabase")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
