import os
from pathlib import Path

import psycopg


DB = os.environ["DATABASE_URL"]

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def apply_migrations():
    """Apply idempotent SQL migrations in filename order."""

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migrations:
        raise RuntimeError("No database migrations found")

    applied = []

    with psycopg.connect(DB, autocommit=True) as conn:
        for migration in migrations:
            sql = migration.read_text(encoding="utf-8")

            conn.execute(sql, prepare=False)

            applied.append(migration.name)

            print(f"EVAP migration applied: {migration.name}", flush=True)

    return applied
