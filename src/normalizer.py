import json
from pathlib import Path


# =========================================================
# TAXONOMY FILE LOCATION
# =========================================================

TAXONOMY_PATH = Path("data/taxonomy.json")


# =========================================================
# LOAD TAXONOMY
# =========================================================

def load_taxonomy():
    """
    Load the governed taxonomy from data/taxonomy.json.

    Returns:
        dict: The complete taxonomy.
    """

    if not TAXONOMY_PATH.exists():
        raise FileNotFoundError(
            f"Taxonomy file was not found at: {TAXONOMY_PATH}"
        )

    with open(
        TAXONOMY_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# =========================================================
# SAVE TAXONOMY
# =========================================================

def save_taxonomy(taxonomy):
    """
    Save the complete taxonomy back to data/taxonomy.json.
    """

    TAXONOMY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        TAXONOMY_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            taxonomy,
            file,
            ensure_ascii=False,
            indent=2,
        )


# =========================================================
# NORMALIZE A VALUE
# =========================================================

def normalize_value(
    raw_value,
    category,
    taxonomy,
):
    """
    Try to resolve a raw source value against an existing
    governed taxonomy alias.

    Example:

        Deutschland -> Germany
        Premium Kaffee -> Premium Coffee

    Returns:
        str: Canonical value when a match is found.
        None: When no match exists.
    """

    if raw_value is None:
        return None

    if category not in taxonomy:
        return None

    raw_value_clean = (
        str(raw_value)
        .strip()
        .casefold()
    )

    category_values = taxonomy.get(
        category,
        {},
    )

    for canonical_value, aliases in (
        category_values.items()
    ):

        # Also allow the canonical value itself
        # to be matched directly.
        if (
            raw_value_clean
            == str(canonical_value)
            .strip()
            .casefold()
        ):
            return canonical_value

        for alias in aliases:

            alias_clean = (
                str(alias)
                .strip()
                .casefold()
            )

            if raw_value_clean == alias_clean:
                return canonical_value

    return None


# =========================================================
# ADD APPROVED ALIAS
# =========================================================

def add_taxonomy_alias(
    category,
    canonical_value,
    new_alias,
    taxonomy,
):
    """
    Add a human-approved source value as an alias
    for an existing canonical taxonomy value.

    Example:

        Café Supremo -> Premium Coffee

    The updated taxonomy is written to taxonomy.json.

    Returns:
        bool:
            True  -> a new alias was added
            False -> alias already existed
    """

    if not category:
        raise ValueError(
            "A taxonomy category is required."
        )

    if not canonical_value:
        raise ValueError(
            "A canonical value is required."
        )

    if not new_alias:
        raise ValueError(
            "A new alias is required."
        )


    # -----------------------------------------------------
    # CREATE CATEGORY IF NECESSARY
    # -----------------------------------------------------

    if category not in taxonomy:
        taxonomy[category] = {}


    # -----------------------------------------------------
    # CREATE CANONICAL VALUE IF NECESSARY
    # -----------------------------------------------------

    if canonical_value not in taxonomy[category]:
        taxonomy[category][canonical_value] = []


    aliases = taxonomy[
        category
    ][canonical_value]


    # -----------------------------------------------------
    # CHECK WHETHER ALIAS ALREADY EXISTS
    # -----------------------------------------------------

    new_alias_clean = (
        str(new_alias)
        .strip()
        .casefold()
    )

    existing_aliases = [
        str(alias)
        .strip()
        .casefold()
        for alias in aliases
    ]


    # Also treat the canonical value itself as existing.
    canonical_clean = (
        str(canonical_value)
        .strip()
        .casefold()
    )


    if (
        new_alias_clean in existing_aliases
        or new_alias_clean == canonical_clean
    ):
        return False


    # -----------------------------------------------------
    # ADD ALIAS
    # -----------------------------------------------------

    aliases.append(
        str(new_alias).strip()
    )


    # -----------------------------------------------------
    # SAVE TO DISK
    # -----------------------------------------------------

    save_taxonomy(
        taxonomy
    )

    return True


# =========================================================
# GET CANONICAL OPTIONS
# =========================================================

def get_canonical_values(
    category,
    taxonomy,
):
    """
    Return all governed canonical values for a category.

    Useful for the Streamlit human-review dropdown.
    """

    if category not in taxonomy:
        return []

    return list(
        taxonomy[
            category
        ].keys()
    )


# =========================================================
# CHECK WHETHER ALIAS EXISTS
# =========================================================

def alias_exists(
    category,
    alias,
    taxonomy,
):
    """
    Check whether an alias already exists anywhere
    within the specified taxonomy category.
    """

    if category not in taxonomy:
        return False

    alias_clean = (
        str(alias)
        .strip()
        .casefold()
    )

    for canonical_value, aliases in (
        taxonomy[category].items()
    ):

        if (
            alias_clean
            == str(canonical_value)
            .strip()
            .casefold()
        ):
            return True

        for existing_alias in aliases:

            if (
                alias_clean
                == str(existing_alias)
                .strip()
                .casefold()
            ):
                return True

    return False