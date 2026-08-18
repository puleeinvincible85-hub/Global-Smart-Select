import streamlit as st

from src.normalizer import load_taxonomy, normalize_value


# ---------------------------------------------------------
# Page setup
# ---------------------------------------------------------

st.set_page_config(
    page_title="Global Smart Select",
    page_icon="🌍",
    layout="centered",
)


# ---------------------------------------------------------
# Load taxonomy
# ---------------------------------------------------------

taxonomy = load_taxonomy()


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title("Global Smart Select")
st.subheader("AI for Multilingual Dimension Intelligence")

st.write(
    "Upload a document or paste multilingual business content and "
    "transform it into governed, standardized dimensions."
)


# ---------------------------------------------------------
# Document input
# ---------------------------------------------------------

st.header("1. Document Input")

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["txt", "csv"],
)

st.write("or")

document_text = st.text_area(
    "Paste document text",
    placeholder="Paste multilingual business content here...",
    height=250,
)


# ---------------------------------------------------------
# Read uploaded file
# ---------------------------------------------------------

if uploaded_file is not None:
    try:
        file_contents = uploaded_file.read().decode("utf-8")

        document_text = file_contents

        st.success(f"Uploaded: {uploaded_file.name}")

        with st.expander("Preview uploaded document"):
            st.text(file_contents)

    except UnicodeDecodeError:
        st.error(
            "The uploaded file could not be read as UTF-8 text. "
            "Please try a different TXT or CSV file."
        )


# ---------------------------------------------------------
# Analyze document
# ---------------------------------------------------------

if st.button("Analyze Document"):
    if not document_text.strip():
        st.warning(
            "Please upload a document or enter document text."
        )
    else:
        st.success(
            "Document received. Automated entity extraction "
            "will be added in the next development step."
        )

        with st.expander("Document received"):
            st.text(document_text)


# ---------------------------------------------------------
# Divider
# ---------------------------------------------------------

st.divider()


# ---------------------------------------------------------
# Taxonomy normalization demo
# ---------------------------------------------------------

st.header("2. Taxonomy Normalization")

st.write(
    "Test how multilingual or alternative terminology is mapped "
    "to a standard enterprise value."
)

test_category = st.selectbox(
    "Select dimension",
    options=["regions", "products"],
)


test_value = st.text_input(
    "Enter a value to normalize",
    placeholder="Example: Deutschland",
)


if st.button("Normalize Value"):
    if not test_value.strip():
        st.warning("Please enter a value.")

    else:
        normalized_value = normalize_value(
            raw_value=test_value,
            category=test_category,
            taxonomy=taxonomy,
        )

        if normalized_value:
            st.success(
                f"{test_value} → {normalized_value}"
            )

            st.write("### Normalization result")

            st.json(
                {
                    "dimension": test_category,
                    "source_value": test_value,
                    "canonical_value": normalized_value,
                    "status": "matched",
                }
            )

        else:
            st.warning(
                "No taxonomy match found. "
                "This value would require AI or human review."
            )

            st.write("### Normalization result")

            st.json(
                {
                    "dimension": test_category,
                    "source_value": test_value,
                    "canonical_value": None,
                    "status": "review_required",
                }
            )


# ---------------------------------------------------------
# Current MVP status
# ---------------------------------------------------------

st.divider()

st.header("3. MVP Status")

st.write(
    "The application currently supports:"
)

st.markdown(
    """
- TXT and CSV document upload
- Manual document text entry
- Seeded enterprise taxonomy
- Multilingual alias matching
- Canonical value normalization
- Detection of values requiring review
"""
)

st.info(
    "Next step: automatically extract business entities "
    "from the uploaded document and send those values "
    "through the taxonomy normalization process."
)