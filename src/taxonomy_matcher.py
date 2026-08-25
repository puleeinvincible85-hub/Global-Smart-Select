from pydantic import BaseModel, Field

from src.ai_extractor import get_openai_client


class TaxonomySuggestion(BaseModel):
    suggested_canonical_value: str | None = Field(
        description=(
            "The best matching canonical value from the supplied taxonomy, "
            "or null if there is no sensible match."
        )
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence that the proposed canonical value is correct."
    )

    reason: str = Field(
        description="Short explanation for the proposed mapping."
    )


def suggest_taxonomy_mapping(
    dimension_name,
    source_value,
    taxonomy_category,
    taxonomy,
):
    """
    Ask AI to compare an unknown source value
    against the governed taxonomy.

    AI is only allowed to choose from existing
    canonical values.
    """

    client = get_openai_client()

    category_values = taxonomy.get(
        taxonomy_category,
        {}
    )

    canonical_values = list(
        category_values.keys()
    )

    if not canonical_values:
        return None

    canonical_list = "\n".join(
        f"- {value}"
        for value in canonical_values
    )

    instructions = f"""
You are an enterprise taxonomy matching engine.

A business document contains this value:

Dimension:
{dimension_name}

Source value:
{source_value}

The governed taxonomy contains ONLY these canonical values:

{canonical_list}

Your task:

1. Decide whether the source value semantically matches one
   of the canonical values.
2. You MUST NOT invent a new canonical value.
3. If there is a reasonable match, return that exact canonical
   value from the supplied list.
4. If there is no sensible match, return null.
5. Give a confidence score between 0 and 1.
6. Explain the reasoning briefly.
"""

    response = client.responses.parse(
        model="gpt-5",
        instructions=instructions,
        input=source_value,
        text_format=TaxonomySuggestion,
    )

    return response.output_parsed