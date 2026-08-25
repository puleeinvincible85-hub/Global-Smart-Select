import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import DimensionDiscoveryResult


load_dotenv(".env")


def get_openai_client():
    """
    Create an OpenAI API client.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY was not found. "
            "Check the .env file."
        )

    return OpenAI(api_key=api_key)


def discover_dimensions(document_text):
    """
    Dynamically discover business dimensions from
    arbitrary document text.
    """

    client = get_openai_client()

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
channel
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

You may discover other dimensions when they are useful.

RULES:

1. Only extract information supported by the document.
2. Never invent values.
3. Preserve source_value exactly as written.
4. Give each dimension a concise normalized name.
5. Provide a confidence score from 0 to 1.
6. Provide a short supporting evidence phrase.
7. Explain briefly why the item is a useful business dimension.
8. Ignore irrelevant or decorative text.
9. Documents may contain multiple languages.
10. Multiple values may exist for the same dimension.
"""

    response = client.responses.parse(
        model="gpt-5",
        instructions=instructions,
        input=document_text,
        text_format=DimensionDiscoveryResult,
    )

    return response.output_parsed