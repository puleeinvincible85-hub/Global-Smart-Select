import json
import re

import pandas as pd
import streamlit as st

from src.ai_extractor import discover_dimensions

from src.document_reader import (
    read_uploaded_document,
)

from src.taxonomy_matcher import (
    suggest_taxonomy_mapping,
)

from src.translator import (
    create_docx_bytes,
    translate_document,
)

from src.database import (
    add_term,
    create_concept,
    create_document,
    create_observation,
    find_concept_by_term,
    get_all_dimension_governance,
    get_concept,
    get_concept_by_display_label,
    get_concepts,
    get_dimension_governance,
    get_learning_stats,
    get_multilingual_terms,
    get_observation_history,
    get_taxonomy_categories,
    govern_new_dimension,
    mark_dimension_informational,
    register_dimension,
    save_review_decision,
    update_dimension_governance,
    update_observation_decision,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Global Smart Select",
    page_icon="🌍",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

SESSION_DEFAULTS = {
    "table_rows": [],
    "structured_output": [],
    "document_language": None,
    "document_id": None,
    "last_document_text": "",
    "translated_text": None,
    "translated_docx": None,
    "translated_language": None,
}


for key, value in SESSION_DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key] = value


# =========================================================
# LANGUAGES
# =========================================================

LANGUAGES = {
    "English": "en",
    "German": "de",
    "Spanish": "es",
    "French": "fr",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Polish": "pl",
    "Japanese": "ja",
    "Chinese": "zh",
    "Korean": "ko",
    "Language not recorded": "und",
}


LANGUAGE_LABELS = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
    "und": "Language not recorded",
}


LANGUAGE_ALIASES = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "en-gb": "en",
    "en-us": "en",

    "de": "de",
    "deu": "de",
    "ger": "de",
    "german": "de",
    "deutsch": "de",
    "de-de": "de",

    "es": "es",
    "spa": "es",
    "spanish": "es",
    "español": "es",
    "espanol": "es",
    "es-es": "es",

    "fr": "fr",
    "fra": "fr",
    "fre": "fr",
    "french": "fr",
    "français": "fr",
    "francais": "fr",
    "fr-fr": "fr",

    "it": "it",
    "ita": "it",
    "italian": "it",
    "italiano": "it",

    "pt": "pt",
    "por": "pt",
    "portuguese": "pt",
    "português": "pt",
    "portugues": "pt",

    "nl": "nl",
    "nld": "nl",
    "dut": "nl",
    "dutch": "nl",
    "nederlands": "nl",

    "pl": "pl",
    "pol": "pl",
    "polish": "pl",
    "polski": "pl",

    "ja": "ja",
    "jpn": "ja",
    "japanese": "ja",
    "日本語": "ja",

    "zh": "zh",
    "zho": "zh",
    "chi": "zh",
    "chinese": "zh",
    "mandarin": "zh",

    "ko": "ko",
    "kor": "ko",
    "korean": "ko",
    "한국어": "ko",
}


# =========================================================
# FRIENDLY LABELS
# =========================================================

GOVERNANCE_STATUS_LABELS = {
    "governed": "✅ Governed",
    "informational": "ℹ️ Informational",
    "pending": "🆕 Decision needed",
}


MAPPING_METHOD_LABELS = {
    "known_multilingual_term":
        "Automatically recognized",

    "ai_suggestion":
        "AI suggestion",

    "human_approved_term":
        "Human approved",

    "human_created_concept":
        "Human added new standard",

    "human_existing_concept":
        "Human linked to existing standard",

    "human_informational":
        "Human marked informational",
}


SOURCE_LABELS = {
    "human_approved":
        "Human approved",

    "human_approved_new_field":
        "Human approved",

    "human_existing_concept":
        "Human approved",

    "concept_creation":
        "Initial standard",

    "mvp_seed":
        "Starting business standard",

    "legacy_migration":
        "Existing taxonomy",

    "seeded":
        "Existing taxonomy",
}


# =========================================================
# LANGUAGE HELPERS
# =========================================================

def normalize_single_language(value):

    if value is None:

        return None


    text = (
        str(value)
        .strip()
        .lower()
    )


    if not text:

        return None


    if text in LANGUAGE_ALIASES:

        return LANGUAGE_ALIASES[text]


    locale_match = re.fullmatch(
        r"([a-z]{2})[-_][a-z]{2}",
        text,
    )


    if locale_match:

        code = locale_match.group(1)

        if code in LANGUAGE_LABELS:

            return code


    if (
        len(text) == 2
        and
        text in LANGUAGE_LABELS
    ):

        return text


    for alias, code in LANGUAGE_ALIASES.items():

        if len(alias) <= 2:

            continue


        if re.search(
            rf"\b{re.escape(alias)}\b",
            text,
        ):

            return code


    return None


def normalise_detected_languages(
    detected_language,
):

    if detected_language is None:

        return []


    if isinstance(
        detected_language,
        (
            list,
            tuple,
            set,
        ),
    ):

        raw_parts = [
            str(value)
            for value in detected_language
        ]


    else:

        text = str(
            detected_language
        )


        text = re.sub(
            r"\s+(and|und|y|et)\s+",
            ",",
            text,
            flags=re.IGNORECASE,
        )


        raw_parts = re.split(
            r"[,;/|]+",
            text,
        )


    codes = []


    for raw_part in raw_parts:

        code = normalize_single_language(
            raw_part.strip()
        )


        if (
            code
            and
            code not in codes
        ):

            codes.append(
                code
            )


    if not codes:

        code = normalize_single_language(
            detected_language
        )


        if code:

            codes.append(
                code
            )


    return codes


def friendly_document_language(
    detected_language,
):

    codes = normalise_detected_languages(
        detected_language
    )


    if not codes:

        return (
            "Language could not be determined"
        )


    return ", ".join(
        LANGUAGE_LABELS.get(
            code,
            code,
        )
        for code in codes
    )


def default_language_index(
    detected_language,
):

    codes = normalise_detected_languages(
        detected_language
    )


    if len(codes) == 1:

        label = LANGUAGE_LABELS.get(
            codes[0]
        )


        if label in LANGUAGES:

            return list(
                LANGUAGES.keys()
            ).index(
                label
            )


    return len(LANGUAGES) - 1


def friendly_language(
    language_code,
):

    if not language_code:

        return (
            "Language not recorded"
        )


    code = normalize_single_language(
        language_code
    )


    if not code:

        return (
            "Language not recorded"
        )


    return LANGUAGE_LABELS.get(
        code,
        code,
    )


# =========================================================
# UI HELPERS
# =========================================================

def friendly_group_name(
    category,
):

    if not category:

        return "—"


    return (
        str(category)
        .replace(
            "_",
            " ",
        )
        .title()
    )


def suggested_group_name(
    dimension_name,
):
    """
    Produce an editable group name for a newly
    discovered business field.

    sales_channel -> sales_channels
    customer_segment -> customer_segments
    """

    value = (
        str(dimension_name)
        .strip()
        .lower()
        .replace(
            " ",
            "_",
        )
    )


    if not value.endswith(
        "s"
    ):

        value = (
            value + "s"
        )


    return value


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

.stApp {
    background-color: #F4F7FB;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

h1, h2, h3 {
    color: #163F5C;
}

.hero-banner {

    background:
        linear-gradient(
            100deg,
            #123B5D,
            #007C83
        );

    padding: 32px 38px;

    border-radius: 16px;

    margin-bottom: 28px;

    box-shadow:
        0 6px 18px
        rgba(18, 59, 93, 0.15);
}

.hero-title {
    color: white;
    font-size: 42px;
    font-weight: 800;
}

.hero-subtitle {
    color: #EAF6F6;
    font-size: 21px;
    margin-top: 10px;
}

.hero-description {
    color: #D4ECEE;
    font-size: 15px;
    margin-top: 12px;
    max-width: 950px;
    line-height: 1.6;
}

div.stButton > button {

    background:
        linear-gradient(
            90deg,
            #006D77,
            #008C95
        );

    color: white;

    border-radius: 9px;

    border: none;

    font-weight: 650;
}

[data-testid="stMetric"] {

    background-color: white;

    border:
        1px solid #DCE6EF;

    padding: 18px;

    border-radius: 14px;

    box-shadow:
        0 3px 9px
        rgba(0, 0, 0, 0.05);
}

[data-testid="stDataFrame"] {
    background-color: white;
    border-radius: 12px;
}

[data-testid="stExpander"] {

    background-color: white;

    border-radius: 12px;

    border:
        1px solid #E0E8EF;
}

.new-field-card {

    background-color: #FFF8E7;

    border:
        1px solid #ECD18A;

    border-radius: 12px;

    padding: 16px;

    margin-bottom: 15px;
}

.knowledge-intro {

    background-color: #EAF4F6;

    border:
        1px solid #C7E1E4;

    border-radius: 12px;

    padding: 18px;

    margin-bottom: 18px;

    color: #163F5C;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# CORE HELPERS
# =========================================================

def build_ai_taxonomy(
    category,
):

    concepts = get_concepts(
        category
    )


    return {
        category: {
            concept[
                "display_label"
            ]: []

            for concept in concepts
        }
    }


def clear_translation():

    st.session_state.translated_text = None

    st.session_state.translated_docx = None

    st.session_state.translated_language = None


def update_approved_row(
    row_index,
    concept,
    mapping_method=(
        "human_approved_term"
    ),
):

    row = (
        st.session_state
        .table_rows[row_index]
    )


    row["Concept ID"] = (
        concept["id"]
    )

    row["Concept Code"] = (
        concept[
            "concept_code"
        ]
    )

    row["Standard Value"] = (
        concept[
            "display_label"
        ]
    )

    row["Suggested Value"] = (
        "—"
    )

    row["Governed"] = True

    row["Governance Status"] = (
        "governed"
    )

    row["Match Confidence"] = (
        1.0
    )

    row["Mapping Method"] = (
        mapping_method
    )

    row["Status"] = (
        "standardized"
    )

    row["Result"] = (
        "✅ Standardized"
    )


    st.session_state.table_rows[
        row_index
    ] = row


    output = (
        st.session_state
        .structured_output[
            row_index
        ]
    )


    output[
        "concept_code"
    ] = concept[
        "concept_code"
    ]

    output[
        "canonical_value"
    ] = concept[
        "display_label"
    ]

    output[
        "suggested_canonical_value"
    ] = None

    output[
        "governed"
    ] = True

    output[
        "governance_status"
    ] = "governed"

    output[
        "mapping_confidence"
    ] = 1.0

    output[
        "mapping_method"
    ] = mapping_method

    output[
        "status"
    ] = "standardized"


    st.session_state.structured_output[
        row_index
    ] = output


def update_new_field_as_governed(
    row_index,
    concept,
    category,
    mapping_method,
):

    row = (
        st.session_state
        .table_rows[
            row_index
        ]
    )


    row[
        "Concept ID"
    ] = concept["id"]

    row[
        "Concept Code"
    ] = concept[
        "concept_code"
    ]

    row[
        "Standard Value"
    ] = concept[
        "display_label"
    ]

    row[
        "Suggested Value"
    ] = "—"

    row[
        "Taxonomy Category"
    ] = category

    row[
        "Governed"
    ] = True

    row[
        "Governance Status"
    ] = "governed"

    row[
        "Match Confidence"
    ] = 1.0

    row[
        "Mapping Method"
    ] = mapping_method

    row[
        "Status"
    ] = "standardized"

    row[
        "Result"
    ] = (
        "✅ Added to standards"
    )


    st.session_state.table_rows[
        row_index
    ] = row


    output = (
        st.session_state
        .structured_output[
            row_index
        ]
    )


    output[
        "concept_code"
    ] = concept[
        "concept_code"
    ]

    output[
        "canonical_value"
    ] = concept[
        "display_label"
    ]

    output[
        "suggested_canonical_value"
    ] = None

    output[
        "governed"
    ] = True

    output[
        "governance_status"
    ] = "governed"

    output[
        "taxonomy_category"
    ] = category

    output[
        "mapping_confidence"
    ] = 1.0

    output[
        "mapping_method"
    ] = mapping_method

    output[
        "status"
    ] = "standardized"


    st.session_state.structured_output[
        row_index
    ] = output


def update_field_as_informational(
    row_index,
):

    row = (
        st.session_state
        .table_rows[
            row_index
        ]
    )


    row[
        "Governed"
    ] = False

    row[
        "Governance Status"
    ] = (
        "informational"
    )

    row[
        "Status"
    ] = (
        "informational"
    )

    row[
        "Result"
    ] = (
        "ℹ️ Informational"
    )

    row[
        "Mapping Method"
    ] = (
        "human_informational"
    )


    st.session_state.table_rows[
        row_index
    ] = row


    output = (
        st.session_state
        .structured_output[
            row_index
        ]
    )


    output[
        "governed"
    ] = False

    output[
        "governance_status"
    ] = (
        "informational"
    )

    output[
        "taxonomy_category"
    ] = None

    output[
        "mapping_method"
    ] = (
        "human_informational"
    )

    output[
        "status"
    ] = (
        "informational"
    )


    st.session_state.structured_output[
        row_index
    ] = output


# =========================================================
# HERO
# =========================================================

st.markdown(
    '<div class="hero-banner">'
    '<div class="hero-title">'
    '🌍 Global Smart Select'
    '</div>'
    '<div class="hero-subtitle">'
    'Multilingual terminology → governed business concepts'
    '</div>'
    '<div class="hero-description">'
    'AI discovers business fields from documents, applies '
    'standards your organisation already knows, and asks '
    'for human guidance when new terminology or entirely '
    'new business concepts appear.'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 1. DOCUMENT INPUT
# =========================================================

st.header(
    "1. Add your document"
)


left_input, right_input = (
    st.columns(2)
)


with left_input:

    uploaded_file = (
        st.file_uploader(
            "Upload PDF, Word, TXT or CSV",
            type=[
                "pdf",
                "docx",
                "txt",
                "csv",
            ],
        )
    )


with right_input:

    manual_text = (
        st.text_area(
            "Or paste document text",
            height=160,
            placeholder=(
                "Paste your business "
                "document here..."
            ),
        )
    )


document_text = ""


if uploaded_file is not None:

    try:

        document_text = (
            read_uploaded_document(
                uploaded_file
            )
        )


        st.success(
            f"Ready: "
            f"{uploaded_file.name}"
        )


        with st.expander(
            "Preview document"
        ):

            st.text(
                document_text[
                    :10000
                ]
            )


    except Exception as error:

        st.error(
            f"Could not read document: "
            f"{error}"
        )


elif manual_text.strip():

    document_text = (
        manual_text
    )


# =========================================================
# 2. ANALYSIS
# =========================================================

st.divider()

st.header(
    "2. Understand and standardize"
)


st.write(
    "Known terminology is standardized automatically. "
    "New terminology and newly discovered business fields "
    "are shown for human review."
)


if st.button(
    "✨ Analyze Document",
    type="primary",
):

    if not document_text.strip():

        st.warning(
            "Please add a document first."
        )


    else:

        try:

            clear_translation()


            with st.spinner(
                "Understanding your document..."
            ):

                result = (
                    discover_dimensions(
                        document_text
                    )
                )


            source_name = (
                uploaded_file.name
                if uploaded_file
                is not None
                else
                "Pasted text"
            )


            document_id = (
                create_document(
                    source_name=(
                        source_name
                    ),
                    document_language=(
                        result.document_language
                    ),
                )
            )


            table_rows = []

            structured_output = []


            # =================================================
            # PROCESS EACH DISCOVERED BUSINESS VALUE
            # =================================================

            for dimension in (
                result.dimensions
            ):


                dimension_name = (
                    dimension.dimension
                )

                source_value = (
                    dimension.source_value
                )


                register_dimension(
                    dimension_name
                )


                governance = (
                    get_dimension_governance(
                        dimension_name
                    )
                )


                governed = bool(
                    governance[
                        "governed"
                    ]
                )


                governance_status = (
                    governance.get(
                        "governance_status",
                        "pending",
                    )
                )


                category = (
                    governance[
                        "taxonomy_category"
                    ]
                )


                concept = None

                suggested_concept = None

                suggested_value = None

                match_confidence = None

                match_reason = ""

                mapping_method = None

                known_term_language = None


                # =========================================
                # GOVERNED FIELD
                # =========================================

                if (
                    governed
                    and category
                ):


                    concept = (
                        find_concept_by_term(
                            category=(
                                category
                            ),
                            raw_value=(
                                source_value
                            ),
                        )
                    )


                    if concept:

                        match_confidence = (
                            1.0
                        )

                        mapping_method = (
                            "known_multilingual_term"
                        )

                        known_term_language = (
                            concept.get(
                                "language_code"
                            )
                        )


                    else:

                        existing_concepts = (
                            get_concepts(
                                category
                            )
                        )


                        if existing_concepts:

                            suggestion = (
                                suggest_taxonomy_mapping(

                                    dimension_name=(
                                        dimension_name
                                    ),

                                    source_value=(
                                        source_value
                                    ),

                                    taxonomy_category=(
                                        category
                                    ),

                                    taxonomy=(
                                        build_ai_taxonomy(
                                            category
                                        )
                                    ),

                                )
                            )


                            if (
                                suggestion
                                and
                                suggestion
                                .suggested_canonical_value
                            ):


                                suggested_value = (
                                    suggestion
                                    .suggested_canonical_value
                                )


                                match_confidence = (
                                    suggestion
                                    .confidence
                                )


                                match_reason = (
                                    suggestion
                                    .reason
                                )


                                suggested_concept = (
                                    get_concept_by_display_label(

                                        category=(
                                            category
                                        ),

                                        display_label=(
                                            suggested_value
                                        ),

                                    )
                                )


                                mapping_method = (
                                    "ai_suggestion"
                                )


                # =========================================
                # STATUS
                # =========================================

                if concept:

                    status = (
                        "standardized"
                    )

                    result_label = (
                        "✅ Standardized"
                    )


                elif governed:

                    status = (
                        "mapping_review"
                    )

                    result_label = (
                        "⚠️ Review suggested match"
                    )


                elif (
                    governance_status
                    == "informational"
                ):

                    status = (
                        "informational"
                    )

                    result_label = (
                        "ℹ️ Informational"
                    )


                else:

                    status = (
                        "new_field"
                    )

                    result_label = (
                        "🆕 New business field"
                    )


                concept_id = (
                    concept[
                        "concept_id"
                    ]
                    if concept
                    else None
                )


                suggested_concept_id = (
                    suggested_concept[
                        "id"
                    ]
                    if suggested_concept
                    else None
                )


                # =========================================
                # DOCUMENT-SPECIFIC EVIDENCE
                # =========================================

                observation_id = (
                    create_observation(

                        document_id=(
                            document_id
                        ),

                        dimension_name=(
                            dimension_name
                        ),

                        source_value=(
                            source_value
                        ),

                        source_language=(
                            known_term_language
                        ),

                        concept_id=(
                            concept_id
                        ),

                        suggested_concept_id=(
                            suggested_concept_id
                        ),

                        evidence=(
                            dimension.evidence
                        ),

                        extraction_confidence=(
                            dimension.confidence
                        ),

                        mapping_confidence=(
                            match_confidence
                        ),

                        mapping_method=(
                            mapping_method
                        ),

                        review_status=(
                            status
                        ),

                    )
                )


                standard_label = (
                    concept[
                        "display_label"
                    ]
                    if concept
                    else "—"
                )


                concept_code = (
                    concept[
                        "concept_code"
                    ]
                    if concept
                    else "—"
                )


                table_rows.append(
                    {

                        "Business Field":
                            dimension_name
                            .replace(
                                "_",
                                " ",
                            )
                            .title(),

                        "Internal Dimension":
                            dimension_name,

                        "Found in Document":
                            source_value,

                        "Standard Value":
                            standard_label,

                        "Suggested Value":
                            (
                                suggested_value
                                or "—"
                            ),

                        "Concept Code":
                            concept_code,

                        "Concept ID":
                            concept_id,

                        "Suggested Concept ID":
                            suggested_concept_id,

                        "Taxonomy Category":
                            category,

                        "Governed":
                            governed,

                        "Governance Status":
                            governance_status,

                        "Match Confidence":
                            match_confidence,

                        "Why":
                            match_reason,

                        "Evidence":
                            dimension.evidence,

                        "Observation ID":
                            observation_id,

                        "Mapping Method":
                            mapping_method,

                        "Status":
                            status,

                        "Result":
                            result_label,

                    }
                )


                structured_output.append(
                    {

                        "dimension":
                            dimension_name,

                        "source_value":
                            source_value,

                        "concept_code":
                            (
                                concept_code
                                if concept_code
                                != "—"
                                else None
                            ),

                        "canonical_value":
                            (
                                standard_label
                                if standard_label
                                != "—"
                                else None
                            ),

                        "suggested_canonical_value":
                            suggested_value,

                        "governed":
                            governed,

                        "governance_status":
                            governance_status,

                        "taxonomy_category":
                            category,

                        "evidence":
                            dimension.evidence,

                        "extraction_confidence":
                            dimension.confidence,

                        "mapping_confidence":
                            match_confidence,

                        "mapping_method":
                            mapping_method,

                        "status":
                            status,

                    }
                )


            st.session_state.table_rows = (
                table_rows
            )

            st.session_state.structured_output = (
                structured_output
            )

            st.session_state.document_language = (
                result.document_language
            )

            st.session_state.document_id = (
                document_id
            )

            st.session_state.last_document_text = (
                document_text
            )


        except Exception as error:

            st.error(
                "Analysis failed."
            )

            st.exception(
                error
            )


# =========================================================
# CURRENT RESULTS
# =========================================================

if st.session_state.table_rows:

    rows = (
        st.session_state.table_rows
    )


    st.success(
        "Document understood."
    )


    detected_codes = (
        normalise_detected_languages(
            st.session_state
            .document_language
        )
    )


    language_title = (
        "Detected language"
        if len(detected_codes) == 1
        else
        "Detected languages"
    )


    st.info(
        f"{language_title}: "
        f"{friendly_document_language(st.session_state.document_language)}"
    )


    mapping_reviews = []

    new_fields = []


    for row_index, row in enumerate(
        rows
    ):


        if (
            row["Status"]
            == "mapping_review"
        ):

            mapping_reviews.append(
                (
                    row_index,
                    row,
                )
            )


        elif (
            row["Status"]
            == "new_field"
        ):

            new_fields.append(
                (
                    row_index,
                    row,
                )
            )


    standardized_count = sum(
        row["Status"]
        == "standardized"
        for row in rows
    )


    # =====================================================
    # SUMMARY
    # =====================================================

    s1, s2, s3 = (
        st.columns(3)
    )


    with s1:

        st.metric(
            "Business values found",
            len(rows),
        )


    with s2:

        st.metric(
            "Automatically standardized",
            standardized_count,
        )


    with s3:

        st.metric(
            "Need your attention",
            (
                len(mapping_reviews)
                +
                len(new_fields)
            ),
        )


    # =====================================================
    # RESULTS TABLE
    # =====================================================

    st.markdown(
        "### Results"
    )


    display_rows = []


    for row in rows:


        if (
            row["Standard Value"]
            != "—"
        ):

            display_value = (
                row[
                    "Standard Value"
                ]
            )


        elif (
            row["Suggested Value"]
            != "—"
        ):

            display_value = (
                row[
                    "Suggested Value"
                ]
            )


        else:

            display_value = "—"


        display_rows.append(
            {

                "Business Field":
                    row[
                        "Business Field"
                    ],

                "Found in Document":
                    row[
                        "Found in Document"
                    ],

                "Standard / Suggested Value":
                    display_value,

                "Result":
                    row[
                        "Result"
                    ],

            }
        )


    st.dataframe(
        pd.DataFrame(
            display_rows
        ),
        width="stretch",
        hide_index=True,
    )


    # =====================================================
    # 3. EXISTING FIELD — NEW TERMINOLOGY
    # =====================================================

    if mapping_reviews:

        st.divider()

        st.header(
            "3. Review new terminology"
        )


        st.write(
            "The business field already exists in your "
            "standards, but the terminology found in the "
            "document is new."
        )


        for (
            row_index,
            row,
        ) in mapping_reviews:


            with st.container(
                border=True
            ):


                st.markdown(
                    f"### "
                    f"{row['Business Field']}"
                )


                left, right = (
                    st.columns(2)
                )


                with left:

                    st.caption(
                        "📄 Found in document"
                    )

                    st.markdown(
                        f"## "
                        f"{row['Found in Document']}"
                    )


                    with st.expander(
                        "View evidence"
                    ):

                        st.write(
                            row[
                                "Evidence"
                            ]
                        )


                with right:

                    if (
                        row[
                            "Suggested Value"
                        ]
                        != "—"
                    ):

                        st.caption(
                            "✨ AI suggests"
                        )

                        st.markdown(
                            f"## "
                            f"{row['Suggested Value']}"
                        )


                        if (
                            row[
                                "Match Confidence"
                            ]
                            is not None
                        ):

                            st.progress(
                                row[
                                    "Match Confidence"
                                ]
                            )

                            st.write(
                                f"Confidence: "
                                f"**"
                                f"{row['Match Confidence']:.0%}"
                                f"**"
                            )


                        if row["Why"]:

                            with st.expander(
                                "Why this suggestion?"
                            ):

                                st.write(
                                    row["Why"]
                                )


                    else:

                        st.warning(
                            "No suitable existing "
                            "standard was found."
                        )


                language_name = (
                    st.selectbox(

                        "Language of this term",

                        list(
                            LANGUAGES.keys()
                        ),

                        index=(
                            default_language_index(
                                st.session_state
                                .document_language
                            )
                        ),

                        key=(
                            f"term_language_"
                            f"{row_index}"
                        ),

                    )
                )


                language_code = (
                    LANGUAGES[
                        language_name
                    ]
                )


                category = (
                    row[
                        "Taxonomy Category"
                    ]
                )


                concepts = (
                    get_concepts(
                        category
                    )
                )


                concept_labels = [
                    item[
                        "display_label"
                    ]
                    for item in concepts
                ]


                options = [
                    "Choose a business standard..."
                ] + concept_labels


                default_index = 0


                if (
                    row[
                        "Suggested Value"
                    ]
                    in concept_labels
                ):

                    default_index = (
                        concept_labels.index(
                            row[
                                "Suggested Value"
                            ]
                        )
                        + 1
                    )


                selected_label = (
                    st.selectbox(
                        "Approved standard",
                        options=options,
                        index=default_index,
                        key=(
                            f"concept_choice_"
                            f"{row_index}"
                        ),
                    )
                )


                if st.button(

                    "✅ Approve and learn this terminology",

                    key=(
                        f"approve_term_"
                        f"{row_index}"
                    ),

                    use_container_width=True,

                ):


                    if (
                        selected_label
                        ==
                        "Choose a business standard..."
                    ):

                        st.warning(
                            "Choose a business "
                            "standard first."
                        )


                    elif (
                        language_code
                        == "und"
                    ):

                        st.warning(
                            "Please select the language "
                            "of the term before approving."
                        )


                    else:

                        selected_concept = (
                            get_concept_by_display_label(
                                category=(
                                    category
                                ),
                                display_label=(
                                    selected_label
                                ),
                            )
                        )


                        add_term(
                            concept_id=(
                                selected_concept[
                                    "id"
                                ]
                            ),
                            term=(
                                row[
                                    "Found in Document"
                                ]
                            ),
                            language_code=(
                                language_code
                            ),
                            term_type="alias",
                            source=(
                                "human_approved"
                            ),
                        )


                        update_observation_decision(
                            observation_id=(
                                row[
                                    "Observation ID"
                                ]
                            ),
                            concept_id=(
                                selected_concept[
                                    "id"
                                ]
                            ),
                            mapping_confidence=1.0,
                            mapping_method=(
                                "human_approved_term"
                            ),
                            review_status=(
                                "standardized"
                            ),
                        )


                        save_review_decision(
                            document_id=(
                                st.session_state
                                .document_id
                            ),
                            observation_id=(
                                row[
                                    "Observation ID"
                                ]
                            ),
                            dimension=(
                                row[
                                    "Internal Dimension"
                                ]
                            ),
                            source_value=(
                                row[
                                    "Found in Document"
                                ]
                            ),
                            ai_suggestion=(
                                row[
                                    "Suggested Value"
                                ]
                                if row[
                                    "Suggested Value"
                                ] != "—"
                                else None
                            ),
                            final_canonical_value=(
                                selected_label
                            ),
                            confidence=(
                                row[
                                    "Match Confidence"
                                ]
                            ),
                            decision=(
                                "approved_multilingual_term"
                            ),
                        )


                        update_approved_row(
                            row_index,
                            selected_concept,
                        )


                        st.toast(
                            (
                                "Terminology learned. "
                                "Future documents can "
                                "reuse this mapping."
                            ),
                            icon="🧠",
                        )


                        st.rerun()


    # =====================================================
    # 4. UNKNOWN BUSINESS FIELDS
    # =====================================================

    if new_fields:

        st.divider()

        st.header(
            "4. New business fields discovered"
        )


        st.write(
            "AI found information that is not currently "
            "part of your organisation's business standards. "
            "You decide how it should be governed."
        )


        for (
            row_index,
            row,
        ) in new_fields:


            with st.container(
                border=True
            ):


                st.markdown(
                    f"### 🆕 "
                    f"{row['Business Field']}"
                )


                st.markdown(
                    """
                    <div class="new-field-card">
                    This field is new to the organisation's
                    current business standards. AI has
                    discovered it, but it will not be added
                    automatically without human approval.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


                info_col, evidence_col = (
                    st.columns(2)
                )


                with info_col:

                    st.caption(
                        "Example value found"
                    )

                    st.markdown(
                        f"## "
                        f"{row['Found in Document']}"
                    )


                with evidence_col:

                    st.caption(
                        "Business field"
                    )

                    st.markdown(
                        f"## "
                        f"{row['Business Field']}"
                    )


                with st.expander(
                    "View source evidence"
                ):

                    st.write(
                        row[
                            "Evidence"
                        ]
                    )


                st.markdown(
                    "#### What should happen?"
                )


                field_decision = (
                    st.radio(

                        "Choose how this new business field should be handled",

                        options=[
                            "Add to Business Standards",
                            "Keep as Informational",
                        ],

                        key=(
                            f"field_decision_"
                            f"{row_index}"
                        ),

                    )
                )


                # =========================================
                # INFORMATIONAL
                # =========================================

                if (
                    field_decision
                    ==
                    "Keep as Informational"
                ):


                    st.info(
                        "The field will still appear in "
                        "document results, but values will "
                        "not be standardized against a "
                        "business taxonomy."
                    )


                    if st.button(

                        "Save as Informational",

                        key=(
                            f"informational_"
                            f"{row_index}"
                        ),

                        use_container_width=True,

                    ):


                        mark_dimension_informational(
                            row[
                                "Internal Dimension"
                            ]
                        )


                        update_observation_decision(
                            observation_id=(
                                row[
                                    "Observation ID"
                                ]
                            ),
                            concept_id=None,
                            mapping_confidence=None,
                            mapping_method=(
                                "human_informational"
                            ),
                            review_status=(
                                "informational"
                            ),
                        )


                        save_review_decision(
                            document_id=(
                                st.session_state
                                .document_id
                            ),
                            observation_id=(
                                row[
                                    "Observation ID"
                                ]
                            ),
                            dimension=(
                                row[
                                    "Internal Dimension"
                                ]
                            ),
                            source_value=(
                                row[
                                    "Found in Document"
                                ]
                            ),
                            ai_suggestion=None,
                            final_canonical_value=None,
                            confidence=None,
                            decision=(
                                "informational_field"
                            ),
                        )


                        update_field_as_informational(
                            row_index
                        )


                        st.toast(
                            "Field saved as informational.",
                            icon="ℹ️",
                        )


                        st.rerun()


                # =========================================
                # GOVERN FIELD
                # =========================================

                else:


                    st.markdown(
                        "#### Add this field to your standards"
                    )


                    existing_categories = (
                        get_taxonomy_categories()
                    )


                    group_mode_options = []


                    if existing_categories:

                        group_mode_options.append(
                            "Use an existing standard group"
                        )


                    group_mode_options.append(
                        "Create a new standard group"
                    )


                    group_mode = (
                        st.radio(

                            "Standard group",

                            options=(
                                group_mode_options
                            ),

                            key=(
                                f"group_mode_"
                                f"{row_index}"
                            ),

                        )
                    )


                    selected_category = None


                    # =====================================
                    # EXISTING GROUP
                    # =====================================

                    if (
                        group_mode
                        ==
                        "Use an existing standard group"
                    ):


                        category_labels = {
                            friendly_group_name(
                                category
                            ):
                            category

                            for category
                            in existing_categories
                        }


                        selected_group_label = (
                            st.selectbox(

                                "Choose the existing standard group",

                                list(
                                    category_labels.keys()
                                ),

                                key=(
                                    f"existing_group_"
                                    f"{row_index}"
                                ),

                            )
                        )


                        selected_category = (
                            category_labels[
                                selected_group_label
                            ]
                        )


                        group_concepts = (
                            get_concepts(
                                selected_category
                            )
                        )


                        value_mode = (
                            st.radio(

                                "What about the value found in this document?",

                                options=[
                                    "Match it to an existing standard value",
                                    "Create a new standard value",
                                ],

                                key=(
                                    f"value_mode_"
                                    f"{row_index}"
                                ),

                            )
                        )


                        # =================================
                        # EXISTING GROUP + EXISTING VALUE
                        # =================================

                        if (
                            value_mode
                            ==
                            "Match it to an existing standard value"
                        ):


                            concept_labels = [
                                concept[
                                    "display_label"
                                ]
                                for concept
                                in group_concepts
                            ]


                            if not concept_labels:

                                st.warning(
                                    "This standard group does "
                                    "not contain any values yet. "
                                    "Choose 'Create a new standard value'."
                                )


                            else:

                                selected_label = (
                                    st.selectbox(

                                        "Approved standard value",

                                        options=(
                                            concept_labels
                                        ),

                                        key=(
                                            f"existing_concept_"
                                            f"{row_index}"
                                        ),

                                    )
                                )


                                language_name = (
                                    st.selectbox(

                                        "Language of the term found",

                                        list(
                                            LANGUAGES.keys()
                                        ),

                                        index=(
                                            default_language_index(
                                                st.session_state
                                                .document_language
                                            )
                                        ),

                                        key=(
                                            f"existing_group_language_"
                                            f"{row_index}"
                                        ),

                                    )
                                )


                                if st.button(

                                    "✅ Add field and use this standard",

                                    key=(
                                        f"govern_existing_"
                                        f"{row_index}"
                                    ),

                                    use_container_width=True,

                                ):


                                    language_code = (
                                        LANGUAGES[
                                            language_name
                                        ]
                                    )


                                    if (
                                        language_code
                                        == "und"
                                    ):

                                        st.warning(
                                            "Please select the "
                                            "language of the term."
                                        )


                                    else:

                                        concept = (
                                            get_concept_by_display_label(
                                                category=(
                                                    selected_category
                                                ),
                                                display_label=(
                                                    selected_label
                                                ),
                                            )
                                        )


                                        update_dimension_governance(
                                            dimension_name=(
                                                row[
                                                    "Internal Dimension"
                                                ]
                                            ),
                                            governed=True,
                                            taxonomy_category=(
                                                selected_category
                                            ),
                                            display_name=(
                                                row[
                                                    "Business Field"
                                                ]
                                            ),
                                            data_type=(
                                                "dimension"
                                            ),
                                        )


                                        add_term(
                                            concept_id=(
                                                concept[
                                                    "id"
                                                ]
                                            ),
                                            term=(
                                                row[
                                                    "Found in Document"
                                                ]
                                            ),
                                            language_code=(
                                                language_code
                                            ),
                                            term_type=(
                                                "alias"
                                            ),
                                            source=(
                                                "human_existing_concept"
                                            ),
                                        )


                                        update_observation_decision(
                                            observation_id=(
                                                row[
                                                    "Observation ID"
                                                ]
                                            ),
                                            concept_id=(
                                                concept[
                                                    "id"
                                                ]
                                            ),
                                            mapping_confidence=1.0,
                                            mapping_method=(
                                                "human_existing_concept"
                                            ),
                                            review_status=(
                                                "standardized"
                                            ),
                                        )


                                        save_review_decision(
                                            document_id=(
                                                st.session_state
                                                .document_id
                                            ),
                                            observation_id=(
                                                row[
                                                    "Observation ID"
                                                ]
                                            ),
                                            dimension=(
                                                row[
                                                    "Internal Dimension"
                                                ]
                                            ),
                                            source_value=(
                                                row[
                                                    "Found in Document"
                                                ]
                                            ),
                                            ai_suggestion=None,
                                            final_canonical_value=(
                                                selected_label
                                            ),
                                            confidence=None,
                                            decision=(
                                                "new_field_existing_concept"
                                            ),
                                        )


                                        update_new_field_as_governed(
                                            row_index=(
                                                row_index
                                            ),
                                            concept=(
                                                concept
                                            ),
                                            category=(
                                                selected_category
                                            ),
                                            mapping_method=(
                                                "human_existing_concept"
                                            ),
                                        )


                                        st.toast(
                                            (
                                                "New business field "
                                                "linked to an existing "
                                                "business standard."
                                            ),
                                            icon="🧠",
                                        )


                                        st.rerun()


                        # =================================
                        # EXISTING GROUP + NEW VALUE
                        # =================================

                        else:


                            new_standard_value = (
                                st.text_input(

                                    "New approved standard value",

                                    value=(
                                        row[
                                            "Found in Document"
                                        ]
                                    ),

                                    help=(
                                        "Use the organisation's "
                                        "preferred standard wording."
                                    ),

                                    key=(
                                        f"new_existing_group_value_"
                                        f"{row_index}"
                                    ),

                                )
                            )


                            language_name = (
                                st.selectbox(

                                    "Language of the term found",

                                    list(
                                        LANGUAGES.keys()
                                    ),

                                    index=(
                                        default_language_index(
                                            st.session_state
                                            .document_language
                                        )
                                    ),

                                    key=(
                                        f"new_existing_group_language_"
                                        f"{row_index}"
                                    ),

                                )
                            )


                            if st.button(

                                "✅ Add field and new standard value",

                                key=(
                                    f"govern_new_value_"
                                    f"{row_index}"
                                ),

                                use_container_width=True,

                            ):


                                language_code = (
                                    LANGUAGES[
                                        language_name
                                    ]
                                )


                                if not (
                                    new_standard_value
                                    .strip()
                                ):

                                    st.warning(
                                        "Enter the approved "
                                        "standard value."
                                    )


                                elif (
                                    language_code
                                    == "und"
                                ):

                                    st.warning(
                                        "Please select the "
                                        "language of the term."
                                    )


                                else:

                                    concept_id = (
                                        create_concept(
                                            category=(
                                                selected_category
                                            ),
                                            display_label=(
                                                new_standard_value
                                            ),
                                        )
                                    )


                                    concept = (
                                        get_concept(
                                            concept_id
                                        )
                                    )


                                    update_dimension_governance(
                                        dimension_name=(
                                            row[
                                                "Internal Dimension"
                                            ]
                                        ),
                                        governed=True,
                                        taxonomy_category=(
                                            selected_category
                                        ),
                                        display_name=(
                                            row[
                                                "Business Field"
                                            ]
                                        ),
                                        data_type=(
                                            "dimension"
                                        ),
                                    )


                                    if (
                                        str(
                                            row[
                                                "Found in Document"
                                            ]
                                        )
                                        .strip()
                                        .casefold()
                                        !=
                                        str(
                                            new_standard_value
                                        )
                                        .strip()
                                        .casefold()
                                    ):

                                        add_term(
                                            concept_id=(
                                                concept_id
                                            ),
                                            term=(
                                                row[
                                                    "Found in Document"
                                                ]
                                            ),
                                            language_code=(
                                                language_code
                                            ),
                                            term_type=(
                                                "alias"
                                            ),
                                            source=(
                                                "human_approved_new_field"
                                            ),
                                        )


                                    update_observation_decision(
                                        observation_id=(
                                            row[
                                                "Observation ID"
                                            ]
                                        ),
                                        concept_id=(
                                            concept_id
                                        ),
                                        mapping_confidence=1.0,
                                        mapping_method=(
                                            "human_created_concept"
                                        ),
                                        review_status=(
                                            "standardized"
                                        ),
                                    )


                                    save_review_decision(
                                        document_id=(
                                            st.session_state
                                            .document_id
                                        ),
                                        observation_id=(
                                            row[
                                                "Observation ID"
                                            ]
                                        ),
                                        dimension=(
                                            row[
                                                "Internal Dimension"
                                            ]
                                        ),
                                        source_value=(
                                            row[
                                                "Found in Document"
                                            ]
                                        ),
                                        ai_suggestion=None,
                                        final_canonical_value=(
                                            new_standard_value
                                        ),
                                        confidence=None,
                                        decision=(
                                            "new_field_new_concept"
                                        ),
                                    )


                                    update_new_field_as_governed(
                                        row_index=(
                                            row_index
                                        ),
                                        concept=(
                                            concept
                                        ),
                                        category=(
                                            selected_category
                                        ),
                                        mapping_method=(
                                            "human_created_concept"
                                        ),
                                    )


                                    st.toast(
                                        (
                                            "New standard value "
                                            "added to the existing "
                                            "business standard."
                                        ),
                                        icon="🧠",
                                    )


                                    st.rerun()


                    # =====================================
                    # ENTIRELY NEW GROUP
                    # =====================================

                    else:


                        new_category = (
                            st.text_input(

                                "New standard group",

                                value=(
                                    suggested_group_name(
                                        row[
                                            "Internal Dimension"
                                        ]
                                    )
                                ),

                                help=(
                                    "Example: customer_segments "
                                    "or sales_channels"
                                ),

                                key=(
                                    f"new_group_"
                                    f"{row_index}"
                                ),

                            )
                        )


                        first_standard_value = (
                            st.text_input(

                                "First approved standard value",

                                value=(
                                    row[
                                        "Found in Document"
                                    ]
                                ),

                                help=(
                                    "Use your organisation's "
                                    "preferred standard wording."
                                ),

                                key=(
                                    f"first_standard_"
                                    f"{row_index}"
                                ),

                            )
                        )


                        language_name = (
                            st.selectbox(

                                "Language of the term found",

                                list(
                                    LANGUAGES.keys()
                                ),

                                index=(
                                    default_language_index(
                                        st.session_state
                                        .document_language
                                    )
                                ),

                                key=(
                                    f"new_group_language_"
                                    f"{row_index}"
                                ),

                            )
                        )


                        if st.button(

                            "✅ Create new business standard",

                            key=(
                                f"create_group_"
                                f"{row_index}"
                            ),

                            use_container_width=True,

                        ):


                            language_code = (
                                LANGUAGES[
                                    language_name
                                ]
                            )


                            if (
                                not new_category
                                .strip()
                            ):

                                st.warning(
                                    "Enter the new "
                                    "standard group."
                                )


                            elif (
                                not first_standard_value
                                .strip()
                            ):

                                st.warning(
                                    "Enter the first "
                                    "approved standard value."
                                )


                            elif (
                                language_code
                                == "und"
                            ):

                                st.warning(
                                    "Please select the "
                                    "language of the term."
                                )


                            else:

                                concept_id = (
                                    govern_new_dimension(

                                        dimension_name=(
                                            row[
                                                "Internal Dimension"
                                            ]
                                        ),

                                        taxonomy_category=(
                                            new_category
                                        ),

                                        canonical_value=(
                                            first_standard_value
                                        ),

                                        source_value=(
                                            row[
                                                "Found in Document"
                                            ]
                                        ),

                                        source_language=(
                                            language_code
                                        ),

                                    )
                                )


                                concept = (
                                    get_concept(
                                        concept_id
                                    )
                                )


                                update_observation_decision(
                                    observation_id=(
                                        row[
                                            "Observation ID"
                                        ]
                                    ),
                                    concept_id=(
                                        concept_id
                                    ),
                                    mapping_confidence=1.0,
                                    mapping_method=(
                                        "human_created_concept"
                                    ),
                                    review_status=(
                                        "standardized"
                                    ),
                                )


                                save_review_decision(
                                    document_id=(
                                        st.session_state
                                        .document_id
                                    ),
                                    observation_id=(
                                        row[
                                            "Observation ID"
                                        ]
                                    ),
                                    dimension=(
                                        row[
                                            "Internal Dimension"
                                        ]
                                    ),
                                    source_value=(
                                        row[
                                            "Found in Document"
                                        ]
                                    ),
                                    ai_suggestion=None,
                                    final_canonical_value=(
                                        first_standard_value
                                    ),
                                    confidence=None,
                                    decision=(
                                        "new_business_field_governed"
                                    ),
                                )


                                update_new_field_as_governed(
                                    row_index=(
                                        row_index
                                    ),
                                    concept=(
                                        concept
                                    ),
                                    category=(
                                        new_category
                                    ),
                                    mapping_method=(
                                        "human_created_concept"
                                    ),
                                )


                                st.toast(
                                    (
                                        "New business field, "
                                        "standard group and first "
                                        "value created."
                                    ),
                                    icon="🧠",
                                )


                                st.rerun()


    # =====================================================
    # 5. KNOWLEDGE SUMMARY
    # =====================================================

    st.divider()

    st.header(
        "5. What Global Smart Select knows"
    )


    stats = (
        get_learning_stats()
    )


    m1, m2, m3, m4 = (
        st.columns(4)
    )


    with m1:

        st.metric(
            "Business fields governed",
            stats[
                "governed_fields"
            ],
        )


    with m2:

        st.metric(
            "Business standards",
            stats[
                "concepts"
            ],
        )


    with m3:

        st.metric(
            "Known multilingual terms",
            stats[
                "terms"
            ],
        )


    with m4:

        st.metric(
            "Document examples",
            stats[
                "observations"
            ],
        )


    # =====================================================
    # 6. DOWNLOAD
    # =====================================================

    st.divider()

    st.header(
        "6. Download"
    )


    final_json = {

        "document_id":
            st.session_state
            .document_id,

        "document_language":
            st.session_state
            .document_language,

        "detected_languages":
            normalise_detected_languages(
                st.session_state
                .document_language
            ),

        "dimensions":
            st.session_state
            .structured_output,

    }


    download_left, download_right = (
        st.columns(2)
    )


    with download_left:

        st.markdown(
            "### 📦 Structured results"
        )


        st.download_button(

            "⬇️ Download JSON",

            data=(
                json.dumps(
                    final_json,
                    ensure_ascii=False,
                    indent=2,
                )
                .encode(
                    "utf-8"
                )
            ),

            file_name=(
                "global_smart_select_results.json"
            ),

            mime="application/json",

            use_container_width=True,

        )


    with download_right:

        st.markdown(
            "### 🌐 Optional translated document"
        )


        target_language = (
            st.selectbox(
                "Translate into",
                [
                    "English",
                    "French",
                    "German",
                    "Spanish",
                    "Italian",
                    "Portuguese",
                    "Japanese",
                ],
            )
        )


        if st.button(
            "Prepare translated document",
            use_container_width=True,
        ):


            mappings = []


            for row in (
                st.session_state
                .table_rows
            ):


                if (
                    row[
                        "Standard Value"
                    ]
                    != "—"
                    and
                    row[
                        "Status"
                    ]
                    == "standardized"
                ):

                    mappings.append(
                        {

                            "source_value":
                                row[
                                    "Found in Document"
                                ],

                            "canonical_value":
                                row[
                                    "Standard Value"
                                ],

                        }
                    )


            with st.spinner(
                "Preparing translated document..."
            ):


                translated_text = (
                    translate_document(

                        document_text=(
                            st.session_state
                            .last_document_text
                        ),

                        target_language=(
                            target_language
                        ),

                        standard_mappings=(
                            mappings
                        ),

                    )
                )


                translated_docx = (
                    create_docx_bytes(

                        translated_text=(
                            translated_text
                        ),

                        title=(
                            f"Translated Document "
                            f"– {target_language}"
                        ),

                    )
                )


            st.session_state.translated_text = (
                translated_text
            )

            st.session_state.translated_docx = (
                translated_docx
            )

            st.session_state.translated_language = (
                target_language
            )


        if (
            st.session_state
            .translated_docx
            is not None
        ):


            st.download_button(

                "⬇️ Download Translated Word Document",

                data=(
                    st.session_state
                    .translated_docx
                ),

                file_name=(
                    "translated_document.docx"
                ),

                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.wordprocessingml.document"
                ),

                use_container_width=True,

            )


    with st.expander(
        "View structured JSON"
    ):

        st.json(
            final_json
        )


# =========================================================
# BUSINESS KNOWLEDGE & LEARNING
# =========================================================

st.divider()


with st.expander(
    "🧠 Business Knowledge & Learning",
    expanded=False,
):

    st.markdown(
        """
        <div class="knowledge-intro">
        See what your organisation standardizes, which
        multilingual terminology the system knows, and
        where those decisions came from.
        </div>
        """,
        unsafe_allow_html=True,
    )


    (
        standards_tab,
        terminology_tab,
        evidence_tab,
    ) = st.tabs(
        [
            "Business Standards",
            "Learned Terminology",
            "Evidence History",
        ]
    )


    # =====================================================
    # BUSINESS STANDARDS
    # =====================================================

    with standards_tab:

        governance_rows = (
            get_all_dimension_governance()
        )


        business_standards = []


        for rule in governance_rows:


            status = (
                rule.get(
                    "governance_status",
                    "pending",
                )
            )


            business_standards.append(
                {

                    "Business Field":
                        (
                            rule.get(
                                "display_name"
                            )
                            or
                            rule[
                                "dimension_name"
                            ]
                            .replace(
                                "_",
                                " ",
                            )
                            .title()
                        ),

                    "Standard Group":
                        friendly_group_name(
                            rule.get(
                                "taxonomy_category"
                            )
                        ),

                    "Status":
                        GOVERNANCE_STATUS_LABELS.get(
                            status,
                            status,
                        ),

                }
            )


        if business_standards:

            st.dataframe(
                pd.DataFrame(
                    business_standards
                ),
                width="stretch",
                hide_index=True,
            )


        else:

            st.info(
                "No business fields "
                "have been discovered yet."
            )


    # =====================================================
    # LEARNED TERMINOLOGY
    # =====================================================

    with terminology_tab:

        terminology_rows = (
            get_multilingual_terms()
        )


        learned_rows = []


        for item in terminology_rows:


            source = (
                item.get(
                    "source"
                )
            )


            learned_rows.append(
                {

                    "Term Seen":
                        item[
                            "term"
                        ],

                    "Language":
                        friendly_language(
                            item.get(
                                "language_code"
                            )
                        ),

                    "Standard Meaning":
                        item[
                            "display_label"
                        ],

                    "Standard Group":
                        friendly_group_name(
                            item[
                                "category"
                            ]
                        ),

                    "How Learned":
                        SOURCE_LABELS.get(
                            source,
                            (
                                source
                                .replace(
                                    "_",
                                    " ",
                                )
                                .title()
                                if source
                                else
                                "Not recorded"
                            ),
                        ),

                }
            )


        if learned_rows:

            st.dataframe(
                pd.DataFrame(
                    learned_rows
                ),
                width="stretch",
                hide_index=True,
            )


        else:

            st.info(
                "No terminology stored yet."
            )


    # =====================================================
    # EVIDENCE HISTORY
    # =====================================================

    with evidence_tab:

        observations = (
            get_observation_history()
        )


        evidence_rows = []


        for item in observations:


            mapping_method = (
                item.get(
                    "mapping_method"
                )
            )


            evidence_rows.append(
                {

                    "Document":
                        item.get(
                            "source_name",
                            "Document",
                        ),

                    "Business Field":
                        str(
                            item.get(
                                "dimension_name",
                                "",
                            )
                        )
                        .replace(
                            "_",
                            " ",
                        )
                        .title(),

                    "What Was Found":
                        item.get(
                            "source_value"
                        ),

                    "Standardized As":
                        (
                            item.get(
                                "display_label"
                            )
                            or
                            "—"
                        ),

                    "Evidence":
                        item.get(
                            "evidence"
                        ),

                    "Decision":
                        MAPPING_METHOD_LABELS.get(
                            mapping_method,
                            (
                                mapping_method
                                .replace(
                                    "_",
                                    " ",
                                )
                                .title()
                                if mapping_method
                                else
                                "Awaiting decision"
                            ),
                        ),

                }
            )


        if evidence_rows:

            st.dataframe(
                pd.DataFrame(
                    evidence_rows
                ),
                width="stretch",
                hide_index=True,
            )


        else:

            st.info(
                "No document evidence stored yet."
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()


st.caption(
    "Global Smart Select MVP • "
    "Discover • Standardize • Govern • Learn"
)