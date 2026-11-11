from typing import Any

from pydantic import BaseModel, Field


class SearchEntry(BaseModel):
    entry_id: str | None = Field(description="ID of this entry within the subject, if any")
    content: dict[str, Any] = Field(
        description="The metadata document as ingested. Its structure depends on the index."
    )


class SearchSubject(BaseModel):
    subject: str = Field(description="Identifier of the described resource")
    entries: list[SearchEntry] = Field(
        description="Entries (sub-representations) visible to the user"
    )


class FacetBucket(BaseModel):
    value: str | dict[str, str] = Field(
        description="Bucket label, or a {from, to} range ([from, to)) for histogram facets"
    )
    count: int


class FacetResult(BaseModel):
    name: str = Field(description="Facet name, as given in the request")
    value: float | None = Field(default=None, description="Result of a sum or avg facet")
    buckets: list[FacetBucket] | None = Field(
        default=None, description="Buckets of a terms or histogram facet"
    )


class GSearchResult(BaseModel):
    total: int = Field(description="Total number of matching subjects in the index")
    count: int = Field(description="Number of subjects in this response")
    offset: int
    has_next_page: bool
    gmeta: list[SearchSubject] = Field(description="Matching subjects")
    facet_results: list[FacetResult] | None = None
