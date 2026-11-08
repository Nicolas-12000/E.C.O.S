#!/usr/bin/env python3
"""Apply supabase/migrations/*.sql using psycopg (no psql required)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = REPO_ROOT / "supabase" / "migrations"
INIT_SCRIPTS = [
    REPO_ROOT / "scripts" / "supabase_init_01.sql",
    REPO_ROOT / "scripts" / "supabase_init_02.sql",
    REPO_ROOT / "scripts" / "supabase_init_03.sql",
]


def ensure_migrations_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.ecos_schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    conn.commit()


def is_applied(conn: psycopg.Connection, filename: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM public.ecos_schema_migrations WHERE filename = %s",
            (filename,),
        )
        return cur.fetchone() is not None


def mark_applied(conn: psycopg.Connection, filename: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.ecos_schema_migrations (filename)
            VALUES (%s)
            ON CONFLICT (filename) DO NOTHING
            """,
            (filename,),
        )
    conn.commit()


def apply_file(conn: psycopg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    print(f"[migrate] {path.name}")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    mark_applied(conn, path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Supabase SQL migrations")
    parser.add_argument(
        "--with-init",
        action="store_true",
        help="Also run scripts/supabase_init_01..03.sql (empty database)",
    )
    parser.add_argument(
        "--from",
        dest="from_name",
        metavar="FILE",
        help="Only run this migration filename and later (e.g. 0006_dim_departamentos_coords.sql)",
    )
    parser.add_argument(
        "--mark-applied",
        metavar="FILE",
        nargs="*",
        help="Record migrations as applied without executing (e.g. after manual partial run)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run migrations even if already recorded in ecos_schema_migrations",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        print("[error] Set SUPABASE_DB_URL or DATABASE_URL in .env", file=sys.stderr)
        return 1

    files: list[Path] = []
    if args.with_init:
        files.extend(p for p in INIT_SCRIPTS if p.exists())
    files.extend(sorted(MIGRATIONS.glob("*.sql")))
    if args.from_name:
        files = [f for f in files if f.name >= args.from_name]
    if not files:
        print("[error] No migration files found", file=sys.stderr)
        return 1

    with psycopg.connect(url) as conn:
        ensure_migrations_table(conn)

        if args.mark_applied:
            for name in args.mark_applied:
                mark_applied(conn, name)
                print(f"[mark] {name}")
            print("[ok] Marked as applied.")
            return 0

        for path in files:
            if not args.force and is_applied(conn, path.name):
                print(f"[skip] {path.name} (already applied)")
                continue
            try:
                apply_file(conn, path)
            except Exception as exc:
                conn.rollback()
                print(f"[error] {path.name}: {exc}", file=sys.stderr)
                print(
                    "[hint] If this migration was applied before, run:\n"
                    f"  python scripts/migrate_supabase.py --mark-applied {path.name}\n"
                    "Or only newer files:\n"
                    "  python scripts/migrate_supabase.py --from 0006_dim_departamentos_coords.sql",
                    file=sys.stderr,
                )
                return 1

    print("[ok] Supabase migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
