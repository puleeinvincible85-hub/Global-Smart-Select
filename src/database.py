import re
import sqlite3

from datetime import datetime, timezone
from pathlib import Path


# =========================================================
# DATABASE LOCATION
# =========================================================

DB_PATH = Path(
    "data/global_smart_select.db"
)


# =========================================================
# TIME HELPER
# =========================================================

def utc_now():
    """
    Return current UTC time as ISO text.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    """
    Open the SQLite database.
    """

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = (
        sqlite3.Row
    )

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():
    """
    Create all tables required by the MVP.

    This function is safe to run repeatedly.
    Existing data is preserved.
    """

    connection = get_connection()

    cursor = connection.cursor()


    # =====================================================
    # LEGACY TAXONOMY VALUES
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS taxonomy_values (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            category TEXT NOT NULL,

            canonical_value TEXT NOT NULL,

            active INTEGER NOT NULL
                DEFAULT 1,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            UNIQUE(
                category,
                canonical_value
            )
        )
        """
    )


    # =====================================================
    # LEGACY TAXONOMY ALIASES
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS taxonomy_aliases (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            taxonomy_value_id INTEGER NOT NULL,

            alias TEXT NOT NULL,

            source TEXT NOT NULL
                DEFAULT 'seeded',

            created_at TEXT NOT NULL,

            FOREIGN KEY (
                taxonomy_value_id
            )
            REFERENCES taxonomy_values(id)
        )
        """
    )


    # =====================================================
    # MULTILINGUAL TAXONOMY CONCEPTS
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS taxonomy_concepts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            concept_code TEXT NOT NULL UNIQUE,

            category TEXT NOT NULL,

            display_label TEXT NOT NULL,

            description TEXT,

            active INTEGER NOT NULL
                DEFAULT 1,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            UNIQUE(
                category,
                display_label
            )
        )
        """
    )


    # =====================================================
    # MULTILINGUAL TAXONOMY TERMS
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS taxonomy_terms (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            concept_id INTEGER NOT NULL,

            term TEXT NOT NULL,

            language_code TEXT NOT NULL
                DEFAULT 'und',

            term_type TEXT NOT NULL
                DEFAULT 'alias',

            source TEXT NOT NULL
                DEFAULT 'human_approved',

            approved INTEGER NOT NULL
                DEFAULT 1,

            created_at TEXT NOT NULL,

            FOREIGN KEY (
                concept_id
            )
            REFERENCES taxonomy_concepts(id),

            UNIQUE(
                concept_id,
                term,
                language_code
            )
        )
        """
    )


    # =====================================================
    # DOCUMENTS
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source_name TEXT NOT NULL,

            document_language TEXT,

            processed_at TEXT NOT NULL
        )
        """
    )


    # =====================================================
    # DOCUMENT OBSERVATIONS
    # Evidence belongs here, not in the taxonomy.
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS document_observations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id INTEGER NOT NULL,

            dimension_name TEXT NOT NULL,

            source_value TEXT,

            source_language TEXT,

            concept_id INTEGER,

            suggested_concept_id INTEGER,

            evidence TEXT,

            extraction_confidence REAL,

            mapping_confidence REAL,

            mapping_method TEXT,

            review_status TEXT,

            created_at TEXT NOT NULL,

            FOREIGN KEY (
                document_id
            )
            REFERENCES documents(id),

            FOREIGN KEY (
                concept_id
            )
            REFERENCES taxonomy_concepts(id),

            FOREIGN KEY (
                suggested_concept_id
            )
            REFERENCES taxonomy_concepts(id)
        )
        """
    )


    # =====================================================
    # BUSINESS FIELD GOVERNANCE
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS governed_dimensions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            dimension_name TEXT NOT NULL UNIQUE,

            display_name TEXT NOT NULL,

            taxonomy_category TEXT,

            data_type TEXT NOT NULL
                DEFAULT 'dimension',

            governed INTEGER NOT NULL
                DEFAULT 0,

            active INTEGER NOT NULL
                DEFAULT 1,

            governance_status TEXT NOT NULL
                DEFAULT 'pending',

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL
        )
        """
    )


    # Upgrade an older governed_dimensions table.

    cursor.execute(
        """
        PRAGMA table_info(
            governed_dimensions
        )
        """
    )

    governance_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]


    if (
        "governance_status"
        not in governance_columns
    ):

        cursor.execute(
            """
            ALTER TABLE governed_dimensions

            ADD COLUMN governance_status TEXT
            NOT NULL DEFAULT 'pending'
            """
        )


    # =====================================================
    # HUMAN REVIEW AUDIT
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS review_audit (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id INTEGER,

            observation_id INTEGER,

            dimension TEXT,

            source_value TEXT,

            ai_suggestion TEXT,

            final_canonical_value TEXT,

            confidence REAL,

            decision TEXT NOT NULL,

            created_at TEXT NOT NULL
        )
        """
    )


    # Upgrade older audit table.

    cursor.execute(
        """
        PRAGMA table_info(
            review_audit
        )
        """
    )

    audit_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]


    if "document_id" not in audit_columns:

        cursor.execute(
            """
            ALTER TABLE review_audit

            ADD COLUMN document_id INTEGER
            """
        )


    if "observation_id" not in audit_columns:

        cursor.execute(
            """
            ALTER TABLE review_audit

            ADD COLUMN observation_id INTEGER
            """
        )


    connection.commit()

    connection.close()


# =========================================================
# CONCEPT CODE HELPERS
# =========================================================

def _concept_prefix(
    category,
):
    """
    Convert a category such as products into PRODUCT.
    """

    cleaned = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        str(category),
    )

    cleaned = (
        cleaned
        .strip("_")
        .upper()
    )


    if (
        cleaned.endswith("S")
        and len(cleaned) > 1
    ):

        cleaned = cleaned[:-1]


    if not cleaned:

        cleaned = "CONCEPT"


    return cleaned


def _next_concept_code(
    category,
):
    """
    Generate the next concept code.

    Example:
    PRODUCT_001
    PRODUCT_002
    """

    prefix = _concept_prefix(
        category
    )


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT concept_code
        FROM taxonomy_concepts
        WHERE category = ?
        """,
        (
            category,
        ),
    )


    rows = cursor.fetchall()

    connection.close()


    highest_number = 0


    for row in rows:

        code = row["concept_code"]

        match = re.search(
            r"_(\d+)$",
            code,
        )

        if match:

            number = int(
                match.group(1)
            )

            highest_number = max(
                highest_number,
                number,
            )


    next_number = (
        highest_number + 1
    )


    return (
        f"{prefix}_"
        f"{next_number:03d}"
    )


# =========================================================
# TAXONOMY CONCEPTS
# =========================================================

def create_concept(
    category,
    display_label,
    description="",
):
    """
    Create one language-independent business concept.

    Example:

    PRODUCT_001
    display_label = Premium Coffee
    """

    category = (
        str(category)
        .strip()
        .lower()
        .replace(" ", "_")
    )

    display_label = (
        str(display_label)
        .strip()
    )


    if not category:

        raise ValueError(
            "A taxonomy category is required."
        )


    if not display_label:

        raise ValueError(
            "A concept display label is required."
        )


    existing = (
        get_concept_by_display_label(
            category=category,
            display_label=display_label,
        )
    )


    if existing:

        return existing["id"]


    concept_code = (
        _next_concept_code(
            category
        )
    )


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO taxonomy_concepts (

            concept_code,

            category,

            display_label,

            description,

            active,

            created_at,

            updated_at

        )
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (
            concept_code,
            category,
            display_label,
            description,
            utc_now(),
            utc_now(),
        ),
    )


    concept_id = (
        cursor.lastrowid
    )


    connection.commit()

    connection.close()


    # -----------------------------------------------------
    # The display label becomes the default
    # English preferred term.
    # -----------------------------------------------------

    add_term(
        concept_id=concept_id,
        term=display_label,
        language_code="en",
        term_type="preferred",
        source="concept_creation",
    )


    return concept_id


def get_concept(
    concept_id,
):
    """
    Get one business concept by ID.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM taxonomy_concepts

        WHERE id = ?
        AND active = 1
        """,
        (
            concept_id,
        ),
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)


    return None


def get_concept_by_display_label(
    category,
    display_label,
):
    """
    Get a concept from its friendly display label.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM taxonomy_concepts

        WHERE category = ?

        AND LOWER(
            TRIM(display_label)
        )
        =
        LOWER(
            TRIM(?)
        )

        AND active = 1
        """,
        (
            category,
            display_label,
        ),
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)


    return None


def get_concepts(
    category,
):
    """
    Return all active concepts in one business-standard group.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM taxonomy_concepts

        WHERE category = ?
        AND active = 1

        ORDER BY display_label
        """,
        (
            category,
        ),
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


def get_taxonomy_categories():
    """
    Return all active taxonomy categories.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT DISTINCT category
        FROM taxonomy_concepts

        WHERE active = 1

        ORDER BY category
        """
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        row["category"]
        for row in rows
    ]


# =========================================================
# MULTILINGUAL TERMS
# =========================================================

def add_term(
    concept_id,
    term,
    language_code="und",
    term_type="alias",
    source="human_approved",
):
    """
    Add an approved multilingual term to a concept.

    Example:

    PRODUCT_001
    Premium Kaffee
    language_code = de
    """

    term = (
        str(term)
        .strip()
    )


    if not term:

        return False


    language_code = (
        str(language_code)
        .strip()
        .lower()
        or "und"
    )


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT id
        FROM taxonomy_terms

        WHERE concept_id = ?

        AND LOWER(
            TRIM(term)
        )
        =
        LOWER(
            TRIM(?)
        )

        AND language_code = ?
        """,
        (
            concept_id,
            term,
            language_code,
        ),
    )


    existing = cursor.fetchone()


    if existing:

        connection.close()

        return False


    cursor.execute(
        """
        INSERT INTO taxonomy_terms (

            concept_id,

            term,

            language_code,

            term_type,

            source,

            approved,

            created_at

        )
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (
            concept_id,
            term,
            language_code,
            term_type,
            source,
            utc_now(),
        ),
    )


    connection.commit()

    connection.close()

    return True


def get_terms_for_concept(
    concept_id,
):
    """
    Return every approved term for one concept.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM taxonomy_terms

        WHERE concept_id = ?
        AND approved = 1

        ORDER BY
            language_code,
            term_type,
            term
        """,
        (
            concept_id,
        ),
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


def find_concept_by_term(
    category,
    raw_value,
):
    """
    Look up any approved multilingual term.

    Returns the concept if found.
    """

    if raw_value is None:

        return None


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT

            tc.id AS concept_id,

            tc.concept_code,

            tc.category,

            tc.display_label,

            tt.term,

            tt.language_code,

            tt.term_type,

            tt.source

        FROM taxonomy_terms tt

        JOIN taxonomy_concepts tc
            ON tt.concept_id
            = tc.id

        WHERE tc.category = ?

        AND tc.active = 1

        AND tt.approved = 1

        AND LOWER(
            TRIM(tt.term)
        )
        =
        LOWER(
            TRIM(?)
        )

        LIMIT 1
        """,
        (
            category,
            raw_value,
        ),
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)


    return None


def get_multilingual_terms():
    """
    Return the whole multilingual terminology view.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT

            tc.id AS concept_id,

            tc.concept_code,

            tc.category,

            tc.display_label,

            tt.id AS term_id,

            tt.term,

            tt.language_code,

            tt.term_type,

            tt.source,

            tt.created_at

        FROM taxonomy_terms tt

        JOIN taxonomy_concepts tc
            ON tt.concept_id
            = tc.id

        WHERE tc.active = 1

        AND tt.approved = 1

        ORDER BY

            tc.category,

            tc.display_label,

            tt.language_code,

            tt.term
        """
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DOCUMENTS
# =========================================================

def create_document(
    source_name,
    document_language=None,
):
    """
    Create one processing record for a document.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO documents (

            source_name,

            document_language,

            processed_at

        )
        VALUES (?, ?, ?)
        """,
        (
            source_name,
            document_language,
            utc_now(),
        ),
    )


    document_id = (
        cursor.lastrowid
    )


    connection.commit()

    connection.close()


    return document_id


# =========================================================
# DOCUMENT OBSERVATIONS / EVIDENCE
# =========================================================

def create_observation(
    document_id,
    dimension_name,
    source_value,
    source_language=None,
    concept_id=None,
    suggested_concept_id=None,
    evidence=None,
    extraction_confidence=None,
    mapping_confidence=None,
    mapping_method=None,
    review_status=None,
):
    """
    Store one extracted occurrence from one document.

    Evidence belongs here.

    The same term appearing in ten documents therefore
    creates ten observations but only one taxonomy term.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO document_observations (

            document_id,

            dimension_name,

            source_value,

            source_language,

            concept_id,

            suggested_concept_id,

            evidence,

            extraction_confidence,

            mapping_confidence,

            mapping_method,

            review_status,

            created_at

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            dimension_name,
            source_value,
            source_language,
            concept_id,
            suggested_concept_id,
            evidence,
            extraction_confidence,
            mapping_confidence,
            mapping_method,
            review_status,
            utc_now(),
        ),
    )


    observation_id = (
        cursor.lastrowid
    )


    connection.commit()

    connection.close()


    return observation_id


def update_observation_decision(
    observation_id,
    concept_id=None,
    mapping_confidence=None,
    mapping_method=None,
    review_status=None,
):
    """
    Update one observation after human review.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        UPDATE document_observations

        SET

            concept_id = ?,

            mapping_confidence = ?,

            mapping_method = ?,

            review_status = ?

        WHERE id = ?
        """,
        (
            concept_id,
            mapping_confidence,
            mapping_method,
            review_status,
            observation_id,
        ),
    )


    connection.commit()

    connection.close()


def get_observation_history():
    """
    Return document-level evidence joined to concepts.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT

            d.id AS document_id,

            d.source_name,

            d.document_language,

            d.processed_at,

            o.id AS observation_id,

            o.dimension_name,

            o.source_value,

            o.source_language,

            o.evidence,

            o.extraction_confidence,

            o.mapping_confidence,

            o.mapping_method,

            o.review_status,

            tc.concept_code,

            tc.display_label

        FROM document_observations o

        JOIN documents d
            ON o.document_id
            = d.id

        LEFT JOIN taxonomy_concepts tc
            ON o.concept_id
            = tc.id

        ORDER BY o.id DESC
        """
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# BUSINESS FIELD GOVERNANCE
# =========================================================

def register_dimension(
    dimension_name,
    display_name=None,
):
    """
    Register a newly discovered business field.

    New fields start as pending governance.
    """

    dimension_name = (
        str(dimension_name)
        .strip()
    )


    if not display_name:

        display_name = (
            dimension_name
            .replace("_", " ")
            .title()
        )


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT OR IGNORE INTO governed_dimensions (

            dimension_name,

            display_name,

            taxonomy_category,

            data_type,

            governed,

            active,

            governance_status,

            created_at,

            updated_at

        )
        VALUES (
            ?,
            ?,
            NULL,
            'dimension',
            0,
            1,
            'pending',
            ?,
            ?
        )
        """,
        (
            dimension_name,
            display_name,
            utc_now(),
            utc_now(),
        ),
    )


    connection.commit()

    connection.close()


def get_dimension_governance(
    dimension_name,
):
    """
    Return governance configuration for one business field.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM governed_dimensions

        WHERE dimension_name = ?
        AND active = 1
        """,
        (
            dimension_name,
        ),
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)


    return None


def get_all_dimension_governance():
    """
    Return all active field governance settings.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM governed_dimensions

        WHERE active = 1

        ORDER BY display_name
        """
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


def update_dimension_governance(
    dimension_name,
    governed,
    taxonomy_category=None,
    display_name=None,
    data_type="dimension",
):
    """
    Mark a business field as governed or informational.
    """

    register_dimension(
        dimension_name
    )


    current = (
        get_dimension_governance(
            dimension_name
        )
    )


    if not display_name:

        display_name = (
            current["display_name"]
            if current
            else
            dimension_name
            .replace("_", " ")
            .title()
        )


    if governed:

        governance_status = (
            "governed"
        )

    else:

        taxonomy_category = None

        governance_status = (
            "informational"
        )


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        UPDATE governed_dimensions

        SET

            display_name = ?,

            taxonomy_category = ?,

            data_type = ?,

            governed = ?,

            governance_status = ?,

            updated_at = ?

        WHERE dimension_name = ?
        """,
        (
            display_name,
            taxonomy_category,
            data_type,
            1 if governed else 0,
            governance_status,
            utc_now(),
            dimension_name,
        ),
    )


    connection.commit()

    connection.close()


def mark_dimension_informational(
    dimension_name,
):
    """
    Human explicitly decides this business field should
    remain informational rather than standardized.
    """

    update_dimension_governance(
        dimension_name=dimension_name,
        governed=False,
        taxonomy_category=None,
        data_type="informational",
    )


def deactivate_dimension(
    dimension_name,
):
    """
    Deactivate a business field without deleting history.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        UPDATE governed_dimensions

        SET
            active = 0,
            updated_at = ?

        WHERE dimension_name = ?
        """,
        (
            utc_now(),
            dimension_name,
        ),
    )


    connection.commit()

    connection.close()


# =========================================================
# GOVERN A NEW BUSINESS FIELD
# =========================================================

def govern_new_dimension(
    dimension_name,
    taxonomy_category,
    canonical_value,
    source_value,
    source_language="und",
):
    """
    Convert a newly discovered field into a governed
    business standard.

    Example:

    sales_channel
        ↓
    channels
        ↓
    E-commerce

    Online Shop becomes a multilingual term/alias
    of that concept.
    """

    concept_id = create_concept(
        category=taxonomy_category,
        display_label=canonical_value,
    )


    update_dimension_governance(
        dimension_name=dimension_name,
        governed=True,
        taxonomy_category=taxonomy_category,
        display_name=(
            str(dimension_name)
            .replace("_", " ")
            .title()
        ),
        data_type="dimension",
    )


    if source_value:

        source_clean = (
            str(source_value)
            .strip()
        )

        canonical_clean = (
            str(canonical_value)
            .strip()
        )


        if (
            source_clean.casefold()
            !=
            canonical_clean.casefold()
        ):

            add_term(
                concept_id=concept_id,
                term=source_clean,
                language_code=source_language,
                term_type="alias",
                source=(
                    "human_approved_new_field"
                ),
            )


    return concept_id


# =========================================================
# REVIEW AUDIT
# =========================================================

def save_review_decision(
    dimension,
    source_value,
    ai_suggestion,
    final_canonical_value,
    confidence,
    decision,
    document_id=None,
    observation_id=None,
):
    """
    Store a human review decision.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO review_audit (

            document_id,

            observation_id,

            dimension,

            source_value,

            ai_suggestion,

            final_canonical_value,

            confidence,

            decision,

            created_at

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            observation_id,
            dimension,
            source_value,
            ai_suggestion,
            final_canonical_value,
            confidence,
            decision,
            utc_now(),
        ),
    )


    connection.commit()

    connection.close()


def get_review_history():
    """
    Return human review history.
    """

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM review_audit

        ORDER BY id DESC
        """
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# LEARNING STATISTICS
# =========================================================

def get_learning_stats():
    """
    Return learning statistics.

    IMPORTANT:
    This includes both the new multilingual metric names
    and older compatibility keys used by previous app.py
    versions.
    """

    connection = get_connection()

    cursor = connection.cursor()


    # -----------------------------------------------------
    # BUSINESS CONCEPTS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM taxonomy_concepts

        WHERE active = 1
        """
    )

    concepts = (
        cursor.fetchone()["count"]
    )


    # -----------------------------------------------------
    # ALL APPROVED TERMS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM taxonomy_terms

        WHERE approved = 1
        """
    )

    terms = (
        cursor.fetchone()["count"]
    )


    # -----------------------------------------------------
    # HUMAN-TAUGHT TERMS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM taxonomy_terms

        WHERE approved = 1

        AND source LIKE
            'human_approved%'
        """
    )

    learned_terms = (
        cursor.fetchone()["count"]
    )


    # -----------------------------------------------------
    # DOCUMENT OBSERVATIONS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM document_observations
        """
    )

    observations = (
        cursor.fetchone()["count"]
    )


    # -----------------------------------------------------
    # GOVERNED BUSINESS FIELDS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM governed_dimensions

        WHERE governed = 1

        AND active = 1
        """
    )

    governed_fields = (
        cursor.fetchone()["count"]
    )


    # -----------------------------------------------------
    # NUMBER OF PROCESSED DOCUMENTS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM documents
        """
    )

    documents = (
        cursor.fetchone()["count"]
    )


    connection.close()


    return {

        # Current multilingual model
        "concepts":
            concepts,

        "terms":
            terms,

        "learned_terms":
            learned_terms,

        "observations":
            observations,

        "documents":
            documents,

        "governed_fields":
            governed_fields,

        # Compatibility with earlier app.py versions
        "standard_values":
            concepts,

        "canonical_values":
            concepts,

        "aliases":
            terms,

        "human_approvals":
            learned_terms,
    }


# =========================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =========================================================
# These allow older app.py code and existing test scripts
# to continue working while the database uses the new
# multilingual concept structure.
# =========================================================

def add_taxonomy_value(
    category,
    canonical_value,
):
    """
    Compatibility wrapper.

    Creates a multilingual concept.
    """

    return create_concept(
        category=category,
        display_label=canonical_value,
    )


def get_taxonomy_value_id(
    category,
    canonical_value,
):
    """
    Compatibility wrapper.

    Returns concept ID.
    """

    concept = (
        get_concept_by_display_label(
            category=category,
            display_label=canonical_value,
        )
    )


    if concept:

        return concept["id"]


    return None


def get_canonical_values(
    category,
):
    """
    Compatibility wrapper.

    Return concept display labels.
    """

    concepts = get_concepts(
        category
    )


    return [
        concept["display_label"]
        for concept in concepts
    ]


def add_alias(
    taxonomy_value_id,
    alias,
    source="human_approved",
):
    """
    Compatibility wrapper.

    Old alias calls become multilingual terms.
    Language is unknown because older code does not
    provide a language.
    """

    return add_term(
        concept_id=taxonomy_value_id,
        term=alias,
        language_code="und",
        term_type="alias",
        source=source,
    )


def find_exact_match(
    category,
    raw_value,
):
    """
    Compatibility wrapper.

    Return concept display label for a known term.
    """

    match = find_concept_by_term(
        category=category,
        raw_value=raw_value,
    )


    if match:

        return match[
            "display_label"
        ]


    return None


def get_all_aliases(
    category=None,
):
    """
    Compatibility helper for old admin/learning UI.
    """

    connection = get_connection()

    cursor = connection.cursor()


    if category:

        cursor.execute(
            """
            SELECT

                tt.id,

                tt.term AS alias,

                tt.source,

                tt.created_at,

                tt.language_code,

                tc.category,

                tc.display_label
                    AS canonical_value

            FROM taxonomy_terms tt

            JOIN taxonomy_concepts tc
                ON tt.concept_id
                = tc.id

            WHERE tc.category = ?

            AND tt.approved = 1

            ORDER BY tt.id DESC
            """,
            (
                category,
            ),
        )


    else:

        cursor.execute(
            """
            SELECT

                tt.id,

                tt.term AS alias,

                tt.source,

                tt.created_at,

                tt.language_code,

                tc.category,

                tc.display_label
                    AS canonical_value

            FROM taxonomy_terms tt

            JOIN taxonomy_concepts tc
                ON tt.concept_id
                = tc.id

            WHERE tt.approved = 1

            ORDER BY tt.id DESC
            """
        )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# MIGRATE OLD TAXONOMY
# =========================================================

def migrate_legacy_taxonomy():
    """
    Copy existing taxonomy_values and taxonomy_aliases
    into the multilingual concept/term model.

    Existing data is not deleted.

    Legacy aliases are stored with language 'und'
    because their original language was not recorded.
    """

    initialize_database()


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM taxonomy_values

        WHERE active = 1

        ORDER BY id
        """
    )


    legacy_values = (
        cursor.fetchall()
    )


    for value_row in legacy_values:


        category = (
            value_row["category"]
        )


        canonical_value = (
            value_row[
                "canonical_value"
            ]
        )


        concept_id = (
            create_concept(
                category=category,
                display_label=(
                    canonical_value
                ),
            )
        )


        # Ensure canonical English label exists.

        add_term(
            concept_id=concept_id,
            term=canonical_value,
            language_code="en",
            term_type="preferred",
            source="legacy_migration",
        )


        cursor.execute(
            """
            SELECT *
            FROM taxonomy_aliases

            WHERE taxonomy_value_id = ?
            """,
            (
                value_row["id"],
            ),
        )


        aliases = (
            cursor.fetchall()
        )


        for alias_row in aliases:


            add_term(
                concept_id=concept_id,
                term=alias_row[
                    "alias"
                ],
                language_code="und",
                term_type="alias",
                source=(
                    alias_row["source"]
                    or
                    "legacy_migration"
                ),
            )


    connection.close()


# =========================================================
# ENSURE DATABASE EXISTS WHEN MODULE LOADS
# =========================================================

initialize_database()