import json
from pathlib import Path


TAXONOMY_PATH = Path("data/taxonomy.json")


def load_taxonomy():
    """
    Load the taxonomy from the JSON file.
    """
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_value(raw_value, category, taxonomy):
    """
    Convert a raw value into its canonical taxonomy value.

    Example:
        Deutschland -> Germany
    """

    raw_value_clean = raw_value.strip().lower()

    category_values = taxonomy.get(category, {})

    for canonical_value, aliases in category_values.items():
        for alias in aliases:
            if raw_value_clean == alias.strip().lower():
                return canonical_value

    return None