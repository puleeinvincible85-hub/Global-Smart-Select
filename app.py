import json
import re

import pandas as pd
import streamlit as st

from src.ai_extractor import discover_dimensions
from src.document_reader import read_uploaded_document
from src.taxonomy_matcher import suggest_taxonomy_mapping
from src.translator import create_docx_bytes, translate_document
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
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Global Smart Select",
    page_icon="🌍",
    layout="wide",
)

ESCALATION_THRESHOLD = 0.85

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
# LANGUAGE HELPERS
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
    "en": "en", "eng": "en", "english": "en", "en-gb": "en", "en-us": "en",
    "de": "de", "deu": "de", "ger": "de", "german": "de", "deutsch": "de", "de-de": "de",
    "es": "es", "spa": "es", "spanish": "es", "español": "es", "espanol": "es", "es-es": "es",
    "fr": "fr", "fra": "fr", "fre": "fr", "french": "fr", "français": "fr", "francais": "fr", "fr-fr": "fr",
    "it": "it", "ita": "it", "italian": "it", "italiano": "it",
    "pt": "pt", "por": "pt", "portuguese": "pt", "português": "pt", "portugues": "pt",
    "nl": "nl", "nld": "nl", "dut": "nl", "dutch": "nl", "nederlands": "nl",
    "pl": "pl", "pol": "pl", "polish": "pl", "polski": "pl",
    "ja": "ja", "jpn": "ja", "japanese": "ja", "日本語": "ja",
    "zh": "zh", "zho": "zh", "chi": "zh", "chinese": "zh", "mandarin": "zh",
    "ko": "ko", "kor": "ko", "korean": "ko", "한국어": "ko",
}

GOVERNANCE_STATUS_LABELS = {
    "governed": "✅ Governed",
    "informational": "ℹ️ Informational",
    "pending": "🆕 Decision needed",
}

MAPPING_METHOD_LABELS = {
    "known_multilingual_term": "Automatically recognized",
    "ai_suggestion": "AI suggestion",
    "human_approved_term": "Human approved",
    "human_created_concept": "Human added new standard",
    "human_existing_concept": "Human linked to existing standard",
    "human_informational": "Human marked informational",
}

SOURCE_LABELS = {
    "human_approved": "Human approved",
    "human_approved_new_field": "Human approved",
    "human_existing_concept": "Human approved",
    "concept_creation": "Initial standard",
    "mvp_seed": "Starting business standard",
    "legacy_migration": "Existing taxonomy",
    "seeded": "Existing taxonomy",
}


def normalize_single_language(value):
    if value is None:
        return None

    text = str(value).strip().lower()
    if not text:
        return None

    if text in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[text]

    locale_match = re.fullmatch(r"([a-z]{2})[-_][a-z]{2}", text)
    if locale_match:
        code = locale_match.group(1)
        if code in LANGUAGE_LABELS:
            return code

    if len(text) == 2 and text in LANGUAGE_LABELS:
        return text

    for alias, code in LANGUAGE_ALIASES.items():
        if len(alias) <= 2:
            continue
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return code

    return None


def normalise_detected_languages(detected_language):
    if detected_language is None:
        return []

    if isinstance(detected_language, (list, tuple, set)):
        raw_parts = [str(value) for value in detected_language]
    else:
        text = str(detected_language)
        text = re.sub(r"\s+(and|und|y|et)\s+", ",", text, flags=re.IGNORECASE)
        raw_parts = re.split(r"[,;/|]+", text)

    codes = []
    for raw_part in raw_parts:
        code = normalize_single_language(raw_part.strip())
        if code and code not in codes:
            codes.append(code)

    if not codes:
        code = normalize_single_language(detected_language)
        if code:
            codes.append(code)

    return codes


def friendly_document_language(detected_language):
    codes = normalise_detected_languages(detected_language)
    if not codes:
        return "Language could not be determined"
    return ", ".join(LANGUAGE_LABELS.get(code, code) for code in codes)


def default_language_index(detected_language):
    codes = normalise_detected_languages(detected_language)
    if len(codes) == 1:
        label = LANGUAGE_LABELS.get(codes[0])
        if label in LANGUAGES:
            return list(LANGUAGES.keys()).index(label)
    return len(LANGUAGES) - 1


def friendly_language(language_code):
    code = normalize_single_language(language_code)
    if not code:
        return "Language not recorded"
    return LANGUAGE_LABELS.get(code, code)


# =========================================================
# BUSINESS HELPERS
# =========================================================


def friendly_group_name(category):
    if not category:
        return "—"
    return str(category).replace("_", " ").title()


def suggested_group_name(dimension_name):
    value = str(dimension_name).strip().lower().replace(" ", "_")
    if value and not value.endswith("s"):
        value += "s"
    return value or "new_standard_group"


def confidence_label(value):
    if value is None:
        return "—"
    return f"{value:.0%}"


def get_escalation_team(dimension_name):
    dimension = str(dimension_name).strip().lower()
    team_mapping = {
        "product": "Product Data",
        "brand": "Product Data",
        "category": "Product Data",
        "customer": "Sales Operations",
        "customer_segment": "Sales Operations",
        "country": "Data Governance",
        "region": "Data Governance",
        "market": "Data Governance",
        "sales_channel": "Commercial Operations",
        "channel": "Commercial Operations",
        "revenue": "Finance",
        "sales": "Finance",
        "currency": "Finance",
        "margin": "Finance",
        "growth_rate": "Finance",
    }
    return team_mapping.get(dimension, "Data Governance")


def build_ai_taxonomy(category):
    concepts = get_concepts(category)
    return {category: {concept["display_label"]: [] for concept in concepts}}


def clear_translation():
    st.session_state.translated_text = None
    st.session_state.translated_docx = None
    st.session_state.translated_language = None


def update_structured_output(row_index, updates):
    if row_index < len(st.session_state.structured_output):
        output = st.session_state.structured_output[row_index]
        output.update(updates)
        st.session_state.structured_output[row_index] = output


def update_row_as_standardized(row_index, concept, category, mapping_method):
    row = st.session_state.table_rows[row_index]
    row.update({
        "Concept ID": concept["id"],
        "Concept Code": concept["concept_code"],
        "Standard Value": concept["display_label"],
        "Suggested Value": "—",
        "Taxonomy Category": category,
        "Governed": True,
        "Governance Status": "governed",
        "Match Confidence": 1.0,
        "Mapping Method": mapping_method,
        "Escalation Required": False,
        "Escalation Team": None,
        "Status": "standardized",
        "Result": "✅ Standardized",
    })
    st.session_state.table_rows[row_index] = row

    update_structured_output(
        row_index,
        {
            "concept_code": concept["concept_code"],
            "canonical_value": concept["display_label"],
            "suggested_canonical_value": None,
            "governed": True,
            "governance_status": "governed",
            "taxonomy_category": category,
            "mapping_confidence": 1.0,
            "mapping_method": mapping_method,
            "escalation_required": False,
            "escalation_team": None,
            "status": "standardized",
        },
    )


def update_field_as_informational(row_index):
    row = st.session_state.table_rows[row_index]
    row.update({
        "Governed": False,
        "Governance Status": "informational",
        "Status": "informational",
        "Result": "ℹ️ Informational",
        "Mapping Method": "human_informational",
        "Escalation Required": False,
        "Escalation Team": None,
    })
    st.session_state.table_rows[row_index] = row

    update_structured_output(
        row_index,
        {
            "governed": False,
            "governance_status": "informational",
            "taxonomy_category": None,
            "mapping_method": "human_informational",
            "escalation_required": False,
            "escalation_team": None,
            "status": "informational",
        },
    )


# =========================================================
# STYLES
# =========================================================

st.markdown(
    """
<style>
.stApp { background-color: #F4F7FB; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1450px; }
h1, h2, h3 { color: #163F5C; }
.hero-banner {
    background: linear-gradient(100deg, #123B5D, #007C83);
    padding: 32px 38px;
    border-radius: 16px;
    margin-bottom: 28px;
    box-shadow: 0 6px 18px rgba(18, 59, 93, 0.15);
}
.hero-title { color: white; font-size: 42px; font-weight: 800; }
.hero-subtitle { color: #EAF6F6; font-size: 21px; margin-top: 10px; }
.hero-description { color: #D4ECEE; font-size: 15px; margin-top: 12px; max-width: 950px; line-height: 1.6; }
div.stButton > button {
    background: linear-gradient(90deg, #006D77, #008C95);
    color: white;
    border-radius: 9px;
    border: none;
    font-weight: 650;
}
[data-testid="stMetric"] {
    background-color: white;
    border: 1px solid #DCE6EF;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 3px 9px rgba(0,0,0,0.05);
}
[data-testid="stDataFrame"] { background-color: white; border-radius: 12px; }
[data-testid="stExpander"] { background-color: white; border-radius: 12px; border: 1px solid #E0E8EF; }
.escalation-card {
    background-color: #FFF3E8;
    border: 1px solid #F3B982;
    border-radius: 12px;
    padding: 16px;
    margin: 10px 0 16px 0;
    color: #573A1F;
}
.new-field-card {
    background-color: #FFF8E7;
    border: 1px solid #ECD18A;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 15px;
}
.knowledge-intro {
    background-color: #EAF4F6;
    border: 1px solid #C7E1E4;
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
# HEADER
# =========================================================

st.markdown(
    '<div class="hero-banner">'
    '<div class="hero-title">🌍 Global Smart Select</div>'
    '<div class="hero-subtitle">Multilingual terminology → governed business concepts</div>'
    '<div class="hero-description">AI discovers business fields from documents, applies standards your organisation already knows, escalates uncertain mappings for validation, and learns from approved decisions.</div>'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 1. INPUT
# =========================================================

st.header("1. Add your document")
left_input, right_input = st.columns(2)

with left_input:
    uploaded_file = st.file_uploader(
        "Upload PDF, Word, TXT or CSV",
        type=["pdf", "docx", "txt", "csv"],
    )

with right_input:
    manual_text = st.text_area(
        "Or paste document text",
        height=160,
        placeholder="Paste your multilingual business document here...",
    )

document_text = ""
if uploaded_file is not None:
    try:
        document_text = read_uploaded_document(uploaded_file)
        st.success(f"Ready: {uploaded_file.name}")
        with st.expander("Preview document"):
            st.text(document_text[:10000])
    except Exception as error:
        st.error(f"Could not read document: {error}")
elif manual_text.strip():
    document_text = manual_text


# =========================================================
# 2. ANALYZE
# =========================================================

st.divider()
st.header("2. Understand and standardize")
st.write(
    f"Known terms are standardized automatically. New or uncertain terms below {ESCALATION_THRESHOLD:.0%} confidence are routed for validation."
)

if st.button("✨ Analyze Document", type="primary"):
    if not document_text.strip():
        st.warning("Please add a document first.")
    else:
        try:
            clear_translation()
            with st.spinner("Understanding your document..."):
                result = discover_dimensions(document_text)

            source_name = uploaded_file.name if uploaded_file is not None else "Pasted text"
            document_id = create_document(source_name=source_name, document_language=result.document_language)

            table_rows = []
            structured_output = []

            for dimension in result.dimensions:
                dimension_name = dimension.dimension
                source_value = dimension.source_value

                register_dimension(dimension_name)
                governance = get_dimension_governance(dimension_name)

                governed = bool(governance["governed"])
                governance_status = governance.get("governance_status", "pending")
                category = governance["taxonomy_category"]

                concept = None
                suggested_concept = None
                suggested_value = None
                match_confidence = None
                match_reason = ""
                mapping_method = None
                known_term_language = None
                escalation_required = False
                escalation_team = None

                if governed and category:
                    concept = find_concept_by_term(category=category, raw_value=source_value)

                    if concept:
                        match_confidence = 1.0
                        mapping_method = "known_multilingual_term"
                        known_term_language = concept.get("language_code")
                    else:
                        existing_concepts = get_concepts(category)
                        if existing_concepts:
                            suggestion = suggest_taxonomy_mapping(
                                dimension_name=dimension_name,
                                source_value=source_value,
                                taxonomy_category=category,
                                taxonomy=build_ai_taxonomy(category),
                            )
                            if suggestion and suggestion.suggested_canonical_value:
                                suggested_value = suggestion.suggested_canonical_value
                                match_confidence = suggestion.confidence
                                match_reason = suggestion.reason
                                suggested_concept = get_concept_by_display_label(
                                    category=category,
                                    display_label=suggested_value,
                                )
                                mapping_method = "ai_suggestion"

                if concept:
                    status = "standardized"
                    result_label = "✅ Standardized"
                elif governed:
                    escalation_required = match_confidence is None or match_confidence < ESCALATION_THRESHOLD
                    escalation_team = get_escalation_team(dimension_name) if escalation_required else None
                    if escalation_required:
                        status = "validation_required"
                        result_label = f"⚠️ Validate with {escalation_team}"
                    else:
                        status = "mapping_review"
                        result_label = "✨ Suggested match"
                elif governance_status == "informational":
                    status = "informational"
                    result_label = "ℹ️ Informational"
                else:
                    status = "new_field"
                    result_label = "🆕 New business field"

                concept_id = concept["concept_id"] if concept else None
                suggested_concept_id = suggested_concept["id"] if suggested_concept else None

                observation_id = create_observation(
                    document_id=document_id,
                    dimension_name=dimension_name,
                    source_value=source_value,
                    source_language=known_term_language,
                    concept_id=concept_id,
                    suggested_concept_id=suggested_concept_id,
                    evidence=dimension.evidence,
                    extraction_confidence=dimension.confidence,
                    mapping_confidence=match_confidence,
                    mapping_method=mapping_method,
                    review_status=status,
                )

                standard_label = concept["display_label"] if concept else "—"
                concept_code = concept["concept_code"] if concept else "—"

                table_rows.append(
                    {
                        "Business Field": dimension_name.replace("_", " ").title(),
                        "Internal Dimension": dimension_name,
                        "Found in Document": source_value,
                        "Standard Value": standard_label,
                        "Suggested Value": suggested_value or "—",
                        "Concept Code": concept_code,
                        "Concept ID": concept_id,
                        "Suggested Concept ID": suggested_concept_id,
                        "Taxonomy Category": category,
                        "Governed": governed,
                        "Governance Status": governance_status,
                        "Extraction Confidence": dimension.confidence,
                        "Match Confidence": match_confidence,
                        "Why": match_reason,
                        "Evidence": dimension.evidence,
                        "Observation ID": observation_id,
                        "Mapping Method": mapping_method,
                        "Escalation Required": escalation_required,
                        "Escalation Threshold": ESCALATION_THRESHOLD,
                        "Escalation Team": escalation_team,
                        "Status": status,
                        "Result": result_label,
                    }
                )

                structured_output.append(
                    {
                        "dimension": dimension_name,
                        "source_value": source_value,
                        "concept_code": concept_code if concept_code != "—" else None,
                        "canonical_value": standard_label if standard_label != "—" else None,
                        "suggested_canonical_value": suggested_value,
                        "governed": governed,
                        "governance_status": governance_status,
                        "taxonomy_category": category,
                        "evidence": dimension.evidence,
                        "extraction_confidence": dimension.confidence,
                        "mapping_confidence": match_confidence,
                        "mapping_method": mapping_method,
                        "escalation_required": escalation_required,
                        "escalation_threshold": ESCALATION_THRESHOLD,
                        "escalation_team": escalation_team,
                        "status": status,
                    }
                )

            st.session_state.table_rows = table_rows
            st.session_state.structured_output = structured_output
            st.session_state.document_language = result.document_language
            st.session_state.document_id = document_id
            st.session_state.last_document_text = document_text

        except Exception as error:
            st.error("Analysis failed.")
            st.exception(error)


# =========================================================
# RESULTS
# =========================================================

if st.session_state.table_rows:
    rows = st.session_state.table_rows

    st.success("Document understood.")
    detected_codes = normalise_detected_languages(st.session_state.document_language)
    language_title = "Detected language" if len(detected_codes) == 1 else "Detected languages"
    st.info(f"{language_title}: {friendly_document_language(st.session_state.document_language)}")

    mapping_reviews = []
    new_fields = []
    for row_index, row in enumerate(rows):
        if row["Status"] in ["mapping_review", "validation_required"]:
            mapping_reviews.append((row_index, row))
        elif row["Status"] == "new_field":
            new_fields.append((row_index, row))

    standardized_count = sum(row["Status"] == "standardized" for row in rows)
    validation_count = sum(row["Status"] == "validation_required" for row in rows)

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Business values found", len(rows))
    with s2:
        st.metric("Automatically standardized", standardized_count)
    with s3:
        st.metric("Need attention", len(mapping_reviews) + len(new_fields))
    with s4:
        st.metric("Validation required", validation_count)

    st.markdown("### Results")
    display_rows = []
    for row in rows:
        display_value = row["Standard Value"] if row["Standard Value"] != "—" else row["Suggested Value"]
        display_rows.append(
            {
                "Business Field": row["Business Field"],
                "Found in Document": row["Found in Document"],
                "Standard / Suggested Value": display_value,
                "Confidence": confidence_label(row.get("Match Confidence") or row.get("Extraction Confidence")),
                "Action": row["Result"],
            }
        )
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

    # =====================================================
    # REVIEW EXISTING GOVERNED FIELDS
    # =====================================================

    if mapping_reviews:
        st.divider()
        st.header("3. Review or validate new terminology")
        st.write(
            f"Suggestions below {ESCALATION_THRESHOLD:.0%} mapping confidence are marked for validation by the responsible team."
        )

        for row_index, row in mapping_reviews:
            with st.container(border=True):
                st.markdown(f"### {row['Business Field']}")

                if row.get("Escalation Required"):
                    st.markdown(
                        f"""
                        <div class="escalation-card">
                        <strong>⚠️ Validation required</strong><br><br>
                        Mapping confidence is <strong>{confidence_label(row.get('Match Confidence'))}</strong>, below the
                        <strong>{ESCALATION_THRESHOLD:.0%}</strong> threshold.<br>
                        Recommended owner: <strong>{row.get('Escalation Team')}</strong>.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                left, right = st.columns(2)
                with left:
                    st.caption("📄 Found in document")
                    st.markdown(f"## {row['Found in Document']}")
                    st.write(f"Extraction confidence: **{confidence_label(row.get('Extraction Confidence'))}**")
                    with st.expander("View evidence"):
                        st.write(row["Evidence"])

                with right:
                    if row["Suggested Value"] != "—":
                        st.caption("✨ AI suggests")
                        st.markdown(f"## {row['Suggested Value']}")
                        st.write(f"Mapping confidence: **{confidence_label(row.get('Match Confidence'))}**")
                        if row["Why"]:
                            with st.expander("Why this suggestion?"):
                                st.write(row["Why"])
                    else:
                        st.warning("No suitable existing standard was found.")

                language_name = st.selectbox(
                    "Language of this term",
                    list(LANGUAGES.keys()),
                    index=default_language_index(st.session_state.document_language),
                    key=f"term_language_{row_index}",
                )
                language_code = LANGUAGES[language_name]

                category = row["Taxonomy Category"]
                concepts = get_concepts(category)
                concept_labels = [item["display_label"] for item in concepts]
                options = ["Choose a business standard..."] + concept_labels

                default_index = 0
                if row["Suggested Value"] in concept_labels:
                    default_index = concept_labels.index(row["Suggested Value"]) + 1

                selected_label = st.selectbox(
                    "Approved standard",
                    options=options,
                    index=default_index,
                    key=f"concept_choice_{row_index}",
                )

                if st.button(
                    "✅ Approve and learn this terminology",
                    key=f"approve_term_{row_index}",
                    use_container_width=True,
                ):
                    if selected_label == "Choose a business standard...":
                        st.warning("Choose a business standard first.")
                    elif language_code == "und":
                        st.warning("Please select the language of the term before approving.")
                    else:
                        selected_concept = get_concept_by_display_label(
                            category=category,
                            display_label=selected_label,
                        )

                        add_term(
                            concept_id=selected_concept["id"],
                            term=row["Found in Document"],
                            language_code=language_code,
                            term_type="alias",
                            source="human_approved",
                        )

                        update_observation_decision(
                            observation_id=row["Observation ID"],
                            concept_id=selected_concept["id"],
                            mapping_confidence=1.0,
                            mapping_method="human_approved_term",
                            review_status="standardized",
                        )

                        save_review_decision(
                            document_id=st.session_state.document_id,
                            observation_id=row["Observation ID"],
                            dimension=row["Internal Dimension"],
                            source_value=row["Found in Document"],
                            ai_suggestion=row["Suggested Value"] if row["Suggested Value"] != "—" else None,
                            final_canonical_value=selected_label,
                            confidence=row["Match Confidence"],
                            decision="approved_multilingual_term",
                        )

                        update_row_as_standardized(
                            row_index=row_index,
                            concept=selected_concept,
                            category=category,
                            mapping_method="human_approved_term",
                        )

                        st.toast("Terminology learned. Future documents can reuse this mapping.", icon="🧠")
                        st.rerun()

    # =====================================================
    # NEW BUSINESS FIELDS
    # =====================================================

    if new_fields:
        st.divider()
        st.header("4. New business fields discovered")
        st.write(
            "AI found information that is not currently part of your organisation's business standards. Choose how it should be governed."
        )

        for row_index, row in new_fields:
            with st.container(border=True):
                st.markdown(f"### 🆕 {row['Business Field']}")
                st.markdown(
                    """
                    <div class="new-field-card">
                    This field is new. It will not be added to standards automatically.
                    A human decides whether to link it, create a new value, create a new group, or keep it informational.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2 = st.columns(2)
                with c1:
                    st.caption("Example value found")
                    st.markdown(f"## {row['Found in Document']}")
                with c2:
                    st.caption("Evidence")
                    st.write(row["Evidence"])

                action = st.selectbox(
                    "How should this new field be handled?",
                    options=[
                        "Choose an action...",
                        "Link to an existing standard value",
                        "Add a new value to an existing standard group",
                        "Create a new standard group",
                        "Keep as Informational",
                    ],
                    key=f"new_field_action_{row_index}",
                )

                if action == "Choose an action...":
                    st.info("Select an action to continue.")

                elif action == "Keep as Informational":
                    st.info("The field will appear in document results, but values will not be standardized against a taxonomy.")
                    if st.button("Save as Informational", key=f"informational_{row_index}", use_container_width=True):
                        mark_dimension_informational(row["Internal Dimension"])
                        update_observation_decision(
                            observation_id=row["Observation ID"],
                            concept_id=None,
                            mapping_confidence=None,
                            mapping_method="human_informational",
                            review_status="informational",
                        )
                        save_review_decision(
                            document_id=st.session_state.document_id,
                            observation_id=row["Observation ID"],
                            dimension=row["Internal Dimension"],
                            source_value=row["Found in Document"],
                            ai_suggestion=None,
                            final_canonical_value=None,
                            confidence=None,
                            decision="informational_field",
                        )
                        update_field_as_informational(row_index)
                        st.rerun()

                else:
                    categories = get_taxonomy_categories()

                    if action in [
                        "Link to an existing standard value",
                        "Add a new value to an existing standard group",
                    ] and not categories:
                        st.warning("No existing standard groups are available. Choose 'Create a new standard group'.")
                        continue

                    if action in [
                        "Link to an existing standard value",
                        "Add a new value to an existing standard group",
                    ]:
                        category_labels = {friendly_group_name(category): category for category in categories}
                        selected_group_label = st.selectbox(
                            "Standard group",
                            list(category_labels.keys()),
                            key=f"existing_group_{row_index}",
                        )
                        selected_category = category_labels[selected_group_label]
                    else:
                        selected_category = st.text_input(
                            "New standard group",
                            value=suggested_group_name(row["Internal Dimension"]),
                            help="Example: customer_segments or sales_channels",
                            key=f"new_group_{row_index}",
                        )

                    language_name = st.selectbox(
                        "Language of the term found",
                        list(LANGUAGES.keys()),
                        index=default_language_index(st.session_state.document_language),
                        key=f"new_field_language_{row_index}",
                    )
                    language_code = LANGUAGES[language_name]

                    if action == "Link to an existing standard value":
                        concepts = get_concepts(selected_category)
                        concept_labels = [concept["display_label"] for concept in concepts]
                        if not concept_labels:
                            st.warning("This standard group has no values yet. Choose 'Add a new value to an existing standard group'.")
                            continue

                        selected_label = st.selectbox(
                            "Approved standard value",
                            options=["Choose a value..."] + concept_labels,
                            key=f"existing_concept_{row_index}",
                        )

                        if st.button("✅ Link field to existing standard", key=f"link_existing_{row_index}", use_container_width=True):
                            if selected_label == "Choose a value...":
                                st.warning("Choose a standard value first.")
                            elif language_code == "und":
                                st.warning("Please select the language of the term.")
                            else:
                                concept = get_concept_by_display_label(category=selected_category, display_label=selected_label)
                                update_dimension_governance(
                                    dimension_name=row["Internal Dimension"],
                                    governed=True,
                                    taxonomy_category=selected_category,
                                    display_name=row["Business Field"],
                                    data_type="dimension",
                                )
                                add_term(
                                    concept_id=concept["id"],
                                    term=row["Found in Document"],
                                    language_code=language_code,
                                    term_type="alias",
                                    source="human_existing_concept",
                                )
                                update_observation_decision(
                                    observation_id=row["Observation ID"],
                                    concept_id=concept["id"],
                                    mapping_confidence=1.0,
                                    mapping_method="human_existing_concept",
                                    review_status="standardized",
                                )
                                save_review_decision(
                                    document_id=st.session_state.document_id,
                                    observation_id=row["Observation ID"],
                                    dimension=row["Internal Dimension"],
                                    source_value=row["Found in Document"],
                                    ai_suggestion=None,
                                    final_canonical_value=selected_label,
                                    confidence=None,
                                    decision="new_field_existing_concept",
                                )
                                update_row_as_standardized(row_index, concept, selected_category, "human_existing_concept")
                                st.rerun()

                    elif action == "Add a new value to an existing standard group":
                        new_standard_value = st.text_input(
                            "New approved standard value",
                            value=row["Found in Document"],
                            help="Use the organisation's preferred standard wording.",
                            key=f"new_existing_group_value_{row_index}",
                        )

                        if st.button("✅ Add field and new standard value", key=f"new_value_existing_group_{row_index}", use_container_width=True):
                            if not new_standard_value.strip():
                                st.warning("Enter the approved standard value.")
                            elif language_code == "und":
                                st.warning("Please select the language of the term.")
                            else:
                                concept_id = create_concept(category=selected_category, display_label=new_standard_value.strip())
                                concept = get_concept(concept_id)

                                update_dimension_governance(
                                    dimension_name=row["Internal Dimension"],
                                    governed=True,
                                    taxonomy_category=selected_category,
                                    display_name=row["Business Field"],
                                    data_type="dimension",
                                )

                                if row["Found in Document"].strip().casefold() != new_standard_value.strip().casefold():
                                    add_term(
                                        concept_id=concept_id,
                                        term=row["Found in Document"],
                                        language_code=language_code,
                                        term_type="alias",
                                        source="human_approved_new_field",
                                    )

                                update_observation_decision(
                                    observation_id=row["Observation ID"],
                                    concept_id=concept_id,
                                    mapping_confidence=1.0,
                                    mapping_method="human_created_concept",
                                    review_status="standardized",
                                )
                                save_review_decision(
                                    document_id=st.session_state.document_id,
                                    observation_id=row["Observation ID"],
                                    dimension=row["Internal Dimension"],
                                    source_value=row["Found in Document"],
                                    ai_suggestion=None,
                                    final_canonical_value=new_standard_value.strip(),
                                    confidence=None,
                                    decision="new_field_new_concept",
                                )
                                update_row_as_standardized(row_index, concept, selected_category, "human_created_concept")
                                st.rerun()

                    elif action == "Create a new standard group":
                        first_standard_value = st.text_input(
                            "First approved standard value",
                            value=row["Found in Document"],
                            help="Use your organisation's preferred standard wording.",
                            key=f"first_standard_{row_index}",
                        )

                        if st.button("✅ Create new business standard", key=f"create_group_{row_index}", use_container_width=True):
                            if not selected_category.strip():
                                st.warning("Enter the new standard group.")
                            elif not first_standard_value.strip():
                                st.warning("Enter the first approved standard value.")
                            elif language_code == "und":
                                st.warning("Please select the language of the term.")
                            else:
                                concept_id = govern_new_dimension(
                                    dimension_name=row["Internal Dimension"],
                                    taxonomy_category=selected_category.strip(),
                                    canonical_value=first_standard_value.strip(),
                                    source_value=row["Found in Document"],
                                    source_language=language_code,
                                )
                                concept = get_concept(concept_id)
                                update_observation_decision(
                                    observation_id=row["Observation ID"],
                                    concept_id=concept_id,
                                    mapping_confidence=1.0,
                                    mapping_method="human_created_concept",
                                    review_status="standardized",
                                )
                                save_review_decision(
                                    document_id=st.session_state.document_id,
                                    observation_id=row["Observation ID"],
                                    dimension=row["Internal Dimension"],
                                    source_value=row["Found in Document"],
                                    ai_suggestion=None,
                                    final_canonical_value=first_standard_value.strip(),
                                    confidence=None,
                                    decision="new_business_field_governed",
                                )
                                update_row_as_standardized(row_index, concept, selected_category.strip(), "human_created_concept")
                                st.rerun()

    # =====================================================
    # KNOWLEDGE SUMMARY
    # =====================================================

    st.divider()
    st.header("5. What Global Smart Select knows")
    stats = get_learning_stats()
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Business fields governed", stats["governed_fields"])
    with m2:
        st.metric("Business standards", stats["concepts"])
    with m3:
        st.metric("Known multilingual terms", stats["terms"])
    with m4:
        st.metric("Document examples", stats["observations"])

    # =====================================================
    # DOWNLOADS
    # =====================================================

    st.divider()
    st.header("6. Download")
    final_json = {
        "document_id": st.session_state.document_id,
        "document_language": st.session_state.document_language,
        "detected_languages": normalise_detected_languages(st.session_state.document_language),
        "escalation_threshold": ESCALATION_THRESHOLD,
        "dimensions": st.session_state.structured_output,
    }

    left_download, right_download = st.columns(2)
    with left_download:
        st.markdown("### 📦 Structured results")
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(final_json, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="global_smart_select_results.json",
            mime="application/json",
            use_container_width=True,
        )

    with right_download:
        st.markdown("### 🌐 Optional translated document")
        target_language = st.selectbox(
            "Translate into",
            ["English", "French", "German", "Spanish", "Italian", "Portuguese", "Japanese"],
        )

        if st.button("Prepare translated document", use_container_width=True):
            mappings = []
            for row in st.session_state.table_rows:
                if row["Standard Value"] != "—" and row["Status"] == "standardized":
                    mappings.append(
                        {
                            "source_value": row["Found in Document"],
                            "canonical_value": row["Standard Value"],
                        }
                    )

            with st.spinner("Preparing translated document..."):
                translated_text = translate_document(
                    document_text=st.session_state.last_document_text,
                    target_language=target_language,
                    standard_mappings=mappings,
                )
                translated_docx = create_docx_bytes(
                    translated_text=translated_text,
                    title=f"Translated Document – {target_language}",
                )

            st.session_state.translated_text = translated_text
            st.session_state.translated_docx = translated_docx
            st.session_state.translated_language = target_language

        if st.session_state.translated_docx is not None:
            st.download_button(
                "⬇️ Download Translated Word Document",
                data=st.session_state.translated_docx,
                file_name="translated_document.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    with st.expander("View structured JSON"):
        st.json(final_json)


# =========================================================
# BUSINESS KNOWLEDGE & LEARNING
# =========================================================

st.divider()
with st.expander("🧠 Business Knowledge & Learning", expanded=False):
    st.markdown(
        """
        <div class="knowledge-intro">
        See what your organisation standardizes, which multilingual terminology the system knows,
        and where those decisions came from.
        </div>
        """,
        unsafe_allow_html=True,
    )

    standards_tab, terminology_tab, evidence_tab = st.tabs(
        ["Business Standards", "Learned Terminology", "Evidence History"]
    )

    with standards_tab:
        governance_rows = get_all_dimension_governance()
        business_standards = []
        for rule in governance_rows:
            status = rule.get("governance_status", "pending")
            business_standards.append(
                {
                    "Business Field": rule.get("display_name") or rule["dimension_name"].replace("_", " ").title(),
                    "Standard Group": friendly_group_name(rule.get("taxonomy_category")),
                    "Status": GOVERNANCE_STATUS_LABELS.get(status, status),
                }
            )
        if business_standards:
            st.dataframe(pd.DataFrame(business_standards), use_container_width=True, hide_index=True)
        else:
            st.info("No business fields have been discovered yet.")

    with terminology_tab:
        terminology_rows = get_multilingual_terms()
        learned_rows = []
        for item in terminology_rows:
            source = item.get("source")
            learned_rows.append(
                {
                    "Term Seen": item["term"],
                    "Language": friendly_language(item.get("language_code")),
                    "Standard Meaning": item["display_label"],
                    "Standard Group": friendly_group_name(item["category"]),
                    "How Learned": SOURCE_LABELS.get(
                        source,
                        source.replace("_", " ").title() if source else "Not recorded",
                    ),
                }
            )
        if learned_rows:
            st.dataframe(pd.DataFrame(learned_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No terminology stored yet.")

    with evidence_tab:
        observations = get_observation_history()
        evidence_rows = []
        for item in observations:
            mapping_method = item.get("mapping_method")
            evidence_rows.append(
                {
                    "Document": item.get("source_name", "Document"),
                    "Business Field": str(item.get("dimension_name", "")).replace("_", " ").title(),
                    "What Was Found": item.get("source_value"),
                    "Standardized As": item.get("display_label") or "—",
                    "Evidence": item.get("evidence"),
                    "Decision": MAPPING_METHOD_LABELS.get(
                        mapping_method,
                        mapping_method.replace("_", " ").title() if mapping_method else "Awaiting decision",
                    ),
                }
            )
        if evidence_rows:
            st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No document evidence stored yet.")


# =========================================================
# FOOTER
# =========================================================

st.divider()
st.caption("Global Smart Select MVP • Discover • Standardize • Govern • Escalate • Learn")
