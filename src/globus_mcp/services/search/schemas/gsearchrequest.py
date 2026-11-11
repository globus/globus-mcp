"""
Typed input schema for a Globus Search query (a subset of the GSearchRequest document).

See https://docs.globus.org/api/search/reference/post_query/#gsearchrequest
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Deliberately undescribed: field-name syntax is documented once, in the tool description.
FieldName = str


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- Filters ----


class MatchFilter(_Model):
    type: Literal["match_any", "match_all"] = Field(
        description="match_any: field has at least one of the values. match_all: field has all."
    )
    field_name: FieldName
    values: list[str | bool] = Field(
        description="Values to match. For a boolean field, all values must be booleans."
    )


class RangeValue(_Model):
    """One range. Use EITHER `from`+`to`, OR one of gt/gte plus one of lt/lte."""

    from_: str | float | None = Field(
        default=None,
        alias="from",
        description="Lower bound, or the string '*' for unbounded. Use with `to`.",
    )
    to: str | float | None = Field(
        default=None,
        description="Upper bound, or the string '*' for unbounded. Use with `from`.",
    )
    gte: str | float | None = Field(default=None, description="Lower bound, inclusive.")
    gt: str | float | None = Field(default=None, description="Lower bound, exclusive.")
    lte: str | float | None = Field(default=None, description="Upper bound, inclusive.")
    lt: str | float | None = Field(default=None, description="Upper bound, exclusive.")

    @model_validator(mode="after")
    def _one_style(self) -> "RangeValue":
        has_from_to = self.from_ is not None or self.to is not None
        has_cmp = any(v is not None for v in (self.gte, self.gt, self.lte, self.lt))
        if has_from_to == has_cmp:
            raise ValueError("Specify either from/to, or gt|gte with lt|lte, but not both styles")
        if has_from_to:
            if self.from_ is None or self.to is None:
                raise ValueError("from and to must both be given ('*' means unbounded)")
        elif (self.gte is None) == (self.gt is None) or (self.lte is None) == (self.lt is None):
            raise ValueError("Give exactly one of gte/gt and exactly one of lte/lt")
        return self


class RangeFilter(_Model):
    type: Literal["range"]
    field_name: FieldName
    values: list[RangeValue] = Field(
        description="Ranges over date or numeric values. A document matches if in any range."
    )


class ExistsFilter(_Model):
    type: Literal["exists"]
    field_name: FieldName


class LikeFilter(_Model):
    type: Literal["like"]
    field_name: FieldName = Field(description="A text field. See also `value`.")
    value: str = Field(description="Wildcard pattern: '*' matches any characters, '?' one.")


class LatLon(_Model):
    lat: float
    lon: float


class GeoBoundingBoxFilter(_Model):
    type: Literal["geo_bounding_box"]
    field_name: FieldName
    top_left: LatLon = Field(description="Must be northwest of bottom_right.")
    bottom_right: LatLon


class GeoPolygon(_Model):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]] = Field(
        description=(
            "GeoJSON Polygon coordinates: a single closed ring [[lon, lat], ...] wrapped in a"
            " list, ie [[[lon, lat], [lon, lat], ...]]. Only simple polygons (one ring, no"
            " holes) are allowed."
        )
    )


class GeoShapeFilter(_Model):
    type: Literal["geo_shape"]
    field_name: FieldName
    shape: GeoPolygon
    relation: Literal["intersects", "within"] = "intersects"


class NotFilter(_Model):
    type: Literal["not"]
    filter: "Filter"


class BoolFilter(_Model):
    type: Literal["and", "or"] = Field(description="and: all filters match. or: any matches.")
    filters: list["Filter"]


Filter = Annotated[
    MatchFilter
    | RangeFilter
    | ExistsFilter
    | LikeFilter
    | GeoBoundingBoxFilter
    | GeoShapeFilter
    | NotFilter
    | BoolFilter,
    Field(discriminator="type"),
]
NotFilter.model_rebuild()
BoolFilter.model_rebuild()


# ---- Facets ----


class HistogramRange(_Model):
    low: float | str
    high: float | str


class _FacetBase(_Model):
    name: str | None = Field(
        default=None,
        description=(
            "Name of this facet in the results. Defaults to field_name; must be set if several"
            " facets use the same field."
        ),
    )
    field_name: FieldName


class TermsFacet(_FacetBase):
    type: Literal["terms"]
    size: int | None = Field(default=None, description="Return only the top N buckets.")


class DateHistogramFacet(_FacetBase):
    type: Literal["date_histogram"]
    date_interval: Literal["year", "quarter", "month", "week", "day", "hour", "minute", "second"]
    histogram_range: HistogramRange | None = None


class NumericHistogramFacet(_FacetBase):
    type: Literal["numeric_histogram"]
    size: int = Field(description="Number of histogram intervals.")
    histogram_range: HistogramRange = Field(description="Bounds of the histogram.")


class SumAvgFacet(_FacetBase):
    type: Literal["sum", "avg"]
    missing: float | None = Field(
        default=None, description="Value to assume for docs missing the field (default: ignored)."
    )


Facet = Annotated[
    TermsFacet | DateHistogramFacet | NumericHistogramFacet | SumAvgFacet,
    Field(discriminator="type"),
]


# ---- Boosts and sorting ----


class Boost(_Model):
    field_name: FieldName
    factor: float = Field(
        ge=0, le=10, description="Above 1 raises the rank of matches on this field, below 1 lowers."
    )


class Sort(_Model):
    field_name: FieldName
    order: Literal["asc", "desc"] = "asc"
