import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import DimensionDiscoveryResult


# =========================================================
# LOCAL ENVIRONMENT
# =========================================================

# Loads .env when running locally.
# On Streamlit Cloud there will normally be no .env file,
# which is fine because we also check Streamlit Secrets.

load_dotenv(".env")


# =========================================================
# OPENAI API KEY
# =========================================================

def get_openai_api_key():
    """
    Get the OpenAI API key.

    Priority:

    1. Local environment / .env file
    2. Streamlit Community Cloud Secrets

    This allows the same code to work both locally
    and after deployment.
    """

    # -----------------------------------------------------
    # OPTION 1 — LOCAL .ENV / ENVIRONMENT VARIABLE
    # -----------------------------------------------------

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )


    if api_key:

        return api_key


    # -----------------------------------------------------
    # OPTION 2 — STREAMLIT CLOUD SECRETS
    # -----------------------------------------------------

    try:

        import streamlit as st


        if (
            "OPENAI_API_KEY"
            in st.secrets
        ):

            api_key = (
                st.secrets[
                    "OPENAI_API_KEY"
                ]
            )


            if api_key:

                return str(
                    api_key
                ).strip()


    except Exception:

        # This can happen when the module is being run
        # outside Streamlit.
        pass


    # -----------------------------------------------------
    # NOTHING FOUND
    # -----------------------------------------------------

    raise ValueError(
        "OPENAI_API_KEY was not found. "
        "When running locally, add it to your .env file. "
        "When running on Streamlit Community Cloud, "
        "add OPENAI_API_KEY to the app's Secrets settings."
    )


# =========================================================
# OPENAI CLIENT
# =========================================================

def get_openai_client():
    """
    Create an authenticated OpenAI client.
    """

    api_key = (
        get_openai_api_key()
    )


    return OpenAI(
        api_key=api_key
    )


# =========================================================
# DIMENSION DISCOVERY
# =========================================================

def discover_dimensions(
    document_text,
):
    """
    Dynamically discover important business dimensions
    from arbitrary multilingual document text.

    The document does not need to follow a predefined
    schema.
    """

    if not document_text:

        raise ValueError(
            "Document text cannot be empty."
        )


    if not str(
        document_text
    ).strip():

        raise ValueError(
            "Document text cannot be empty."
        )


    client = (
        get_openai_client()
    )


    instructions = """
You are an enterprise business-data extraction engine.

Analyze the supplied business document and discover its important
business dimensions.

IMPORTANT:

Do not assume that the document follows a predefined schema.

Discover dimensions dynamically from the actual content.

Possible dimensions can include things such as:

organisation
customer
supplier
product
brand
country
region
market
business_unit
sales_channel
customer_segment
currency
revenue
sales
volume
margin
growth_rate
reporting_period
fiscal_year
quarter
KPI
campaign
category

These are examples only.

You may discover other dimensions when they are useful to the
business information contained in the document.

RULES:

1. Only extract information supported by the document.

2. Never invent values.

3. Preserve source_value exactly as written in the document.

4. Give each dimension a concise normalized dimension name.

5. Provide a confidence score from 0 to 1.

6. Provide a short supporting evidence phrase from the document.

7. Explain briefly why the item is a useful business dimension.

8. Ignore irrelevant, decorative, or purely formatting text.

9. Documents may contain one language or multiple languages.

10. Multiple values may exist for the same dimension.

11. Do not translate source_value. Preserve the terminology exactly
    as it appears in the source document.

12. Detect the language or languages actually present in the
    document.

13. If several languages occur in the same document, report all
    detected languages rather than choosing only English.

14. New business fields are allowed. Do not restrict extraction to
    fields already known by the taxonomy.

15. Do not decide whether a newly discovered business field should
    become governed. That governance decision belongs to the human
    review workflow.

The goal is to understand the business information faithfully.
Standardization and governance will be handled after extraction.
"""


    response = (
        client.responses.parse(

            model="gpt-5",

            instructions=(
                instructions
            ),

            input=(
                str(
                    document_text
                )
            ),

            text_format=(
                DimensionDiscoveryResult
            ),

        )
    )


    if (
        response.output_parsed
        is None
    ):

        raise ValueError(
            "OpenAI completed the request but "
            "did not return structured dimension data."
        )


    return (
        response.output_parsed
    )