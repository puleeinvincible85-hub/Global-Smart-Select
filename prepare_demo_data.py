"""
prepare_demo_data.py

Safely clears application records from the existing SQLite database
WITHOUT deleting the database file or table structure, then runs the
project's existing fresh taxonomy and dimension-governance seed scripts.

Run from the project root:

    python prepare_demo_data.py

Optional:
    python prepare_demo_data.py --yes

The --yes flag skips the confirmation prompt.
"""

from __future__ import annotations

import argparse
import runpy
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path("data/global_smart_select.db")

PREFERRED_DELETE_ORDER = [
    "document_observations",
    "documents",
    "review_audit",
    "taxonomy_terms",
    "taxonomy_concepts",
    "taxonomy_aliases",
    "taxonomy_values",
    "governed_dimensions",
]

SEED_SCRIPTS = [
    Path("seed_fresh_taxonomy.py"),
    Path("seed_dimension_governance.py"),
]


def get_existing_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()

    return {
        row[0]
        for row in rows
        if not row[0].startswith("sqlite_")
    }


def create_backup() -> Path:
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"global_smart_select_before_demo_{timestamp}.db"

    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def clear_application_records() -> None:
    connection = sqlite3.connect(DB_PATH)

    try:
        existing_tables = get_existing_tables(connection)

        print("\nExisting application tables:")
        for table_name in sorted(existing_tables):
            print(f"  - {table_name}")

        connection.execute("PRAGMA foreign_keys = OFF")

        deleted_tables = []

        for table_name in PREFERRED_DELETE_ORDER:
            if table_name in existing_tables:
                connection.execute(f'DELETE FROM "{table_name}"')
                deleted_tables.append(table_name)

        remaining_tables = sorted(
            existing_tables.difference(PREFERRED_DELETE_ORDER)
        )

        for table_name in remaining_tables:
            connection.execute(f'DELETE FROM "{table_name}"')
            deleted_tables.append(table_name)

        sequence_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'sqlite_sequence'
            """
        ).fetchone()

        if sequence_exists:
            connection.execute("DELETE FROM sqlite_sequence")

        connection.commit()

        print("\nCleared records from:")
        for table_name in deleted_tables:
            print(f"  - {table_name}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def run_seed_script(script_path: Path) -> None:
    if not script_path.exists():
        raise FileNotFoundError(
            f"Required seed script was not found: {script_path}"
        )

    print(f"\nRunning {script_path.name} ...")
    runpy.run_path(str(script_path), run_name="__main__")


def show_row_counts() -> None:
    connection = sqlite3.connect(DB_PATH)

    try:
        tables = sorted(get_existing_tables(connection))

        print("\nDatabase row counts after preparation:")
        for table_name in tables:
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            print(f"  {table_name}: {count}")

    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Clear Global Smart Select application records and "
            "reseed a clean demo dataset."
        )
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    args = parser.parse_args()

    print("=" * 62)
    print("GLOBAL SMART SELECT - PREPARE CLEAN DEMO DATA")
    print("=" * 62)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database was not found at: {DB_PATH.resolve()}"
        )

    print(f"\nDatabase: {DB_PATH.resolve()}")
    print(
        "\nThis keeps the database file and schema, but removes "
        "all application records before reseeding fresh demo data."
    )

    if not args.yes:
        answer = input(
            "\nType PREPARE to continue: "
        ).strip()

        if answer != "PREPARE":
            print("\nCancelled. No data was changed.")
            return

    backup_path = create_backup()
    print(f"\nBackup created:\n  {backup_path.resolve()}")

    clear_application_records()

    for script_path in SEED_SCRIPTS:
        run_seed_script(script_path)

    show_row_counts()

    print("\n" + "=" * 62)
    print("DEMO DATABASE PREPARATION COMPLETE")
    print("=" * 62)
    print(
        "\nImportant demo check:"
        "\n  Make sure 'Café Supremo' is NOT already an approved term."
        "\n  It should remain new so the MVP can demonstrate AI"
        "\n  suggestion, confidence, escalation and human approval."
    )


if __name__ == "__main__":
    main()
