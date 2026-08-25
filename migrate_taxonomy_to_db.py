import json
from pathlib import Path

from src.database import (
    add_alias,
    add_taxonomy_value,
    initialize_database,
)


TAXONOMY_JSON = Path(
    "data/taxonomy.json"
)


def migrate():
    """
    Import the existing taxonomy.json
    into SQLite.
    """

    if not TAXONOMY_JSON.exists():

        raise FileNotFoundError(
            "data/taxonomy.json was not found."
        )


    with open(
        TAXONOMY_JSON,
        "r",
        encoding="utf-8",
    ) as file:

        taxonomy = json.load(
            file
        )


    initialize_database()


    for category, values in taxonomy.items():

        for canonical_value, aliases in (
            values.items()
        ):

            taxonomy_value_id = (
                add_taxonomy_value(
                    category=category,
                    canonical_value=canonical_value,
                )
            )


            for alias in aliases:

                add_alias(
                    taxonomy_value_id=(
                        taxonomy_value_id
                    ),
                    alias=alias,
                    source="seeded",
                )


    print(
        "Taxonomy migration complete."
    )


if __name__ == "__main__":
    migrate()