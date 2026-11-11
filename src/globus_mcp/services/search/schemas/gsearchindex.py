from typing import Any, Self

from pydantic import BaseModel, Field


class SearchIndex(BaseModel):
    """
    Metadata for a Globus Search index, minus certain admin fields.
    See https://docs.globus.org/api/search/reference/index_show/#gsearchindex
    """

    index_id: str = Field(description="ID of the search index")
    display_name: str = Field(description="Display name of the index")
    description: str | None = Field(default=None, description="Description of the index")
    size_in_mb: int | None = Field(
        default=None,
        description="Current size of the index in MB, rounded down",
    )
    num_subjects: int | None = Field(
        default=None, description="Number of subjects (unique items) in the index"
    )
    num_entries: int | None = Field(
        default=None, description="Number of entries (sub-representations of subjects) in the index"
    )
    creation_date: str | None = Field(
        default=None, description="UTC timestamp of when the index was created"
    )
    content_last_modified_date: str | None = Field(
        default=None,
        description="Time of the last change (ingest or delete), if any.",
    )

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Self:
        """Build from a Globus Search GSearchIndex/IndexWithPermissions API response"""
        return cls(
            index_id=payload["id"],
            display_name=payload["display_name"],
            description=payload.get("description"),
            size_in_mb=payload.get("size_in_mb"),
            num_subjects=payload.get("num_subjects"),
            num_entries=payload.get("num_entries"),
            creation_date=payload.get("creation_date"),
            content_last_modified_date=payload.get("content_last_modified_date"),
        )
