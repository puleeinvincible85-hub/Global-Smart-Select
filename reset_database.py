from pathlib import Path

from src.database import (
    DB_PATH,
    initialize_database,
)


def reset_database():
    """
    Completely remove the current MVP SQLite database
    and create a fresh empty database.

    WARNING:
    This deletes:
    - taxonomy concepts
    - multilingual terms
    - governance decisions
    - documents
    - observations
    - review history
    """

    database_path = Path(DB_PATH)

    if database_path.exists():
        database_path.unlink()

        print(
            f"Deleted old database:\n"
            f"{database_path.resolve()}"
        )

    else:
        print(
            "No existing database was found."
        )

    initialize_database()

    print()
    print(
        "Fresh empty database created successfully."
    )

    print(
        f"Database location:\n"
        f"{database_path.resolve()}"
    )


if __name__ == "__main__":
    reset_database()