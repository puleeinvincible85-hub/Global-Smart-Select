from pydantic import BaseModel, Field


class DiscoveredDimension(BaseModel):
    dimension: str = Field(
        description="Short normalized name for the business dimension."
    )

    source_value: str = Field(
        description="Value exactly as it appears in the source document."
    )

    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence score between 0 and 1."
    )

    evidence: str = Field(
        description="Source phrase supporting the extracted value."
    )

    reason: str = Field(
        description="Why this is a useful business dimension."
    )


class DimensionDiscoveryResult(BaseModel):
    document_language: str
    dimensions: list[DiscoveredDimension]