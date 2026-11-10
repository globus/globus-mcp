"""
Query the contents of a Globus Search index
"""

from typing import Annotated, Any

import globus_sdk
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from globus_mcp.context import GlobusContext
from globus_mcp.services.search.client import get_search_client
from globus_mcp.services.search.schemas.gsearchrequest import Boost, Facet, Filter, Sort
from globus_mcp.services.search.schemas.gsearchresult import (
    FacetBucket,
    FacetResult,
    GSearchResult,
)
from globus_mcp.services.search.util.field_selection import OnlyFields, format_subject


def _dump(items: list[BaseModel] | None) -> list[dict[str, Any]] | None:
    if items is None:
        return None
    return [i.model_dump(mode="json", by_alias=True, exclude_none=True) for i in items]


def _build_query_body(
    *,
    q: str | None,
    advanced: bool,
    filters: list[Any] | None,
    facets: list[Any] | None,
    post_facet_filters: list[Any] | None,
    boosts: list[Any] | None,
    sort: list[Any] | None,
) -> dict[str, Any]:
    # NOTE: The LLM is explicitly never allowed to control admin-only behaviors
    #   like `bypass_visible_to`, `filter_principal_sets`, or `fields`
    body: dict[str, Any] = {
        "advanced": advanced,
        "q": q,
        "filters": _dump(filters),
        "facets": _dump(facets),
        "post_facet_filters": _dump(post_facet_filters),
        "boosts": _dump(boosts),
        "sort": _dump(sort),
    }
    return {k: v for k, v in body.items() if v is not None}


def _format_query_response(
    data: dict[str, Any], only_fields: list[str] | None = None
) -> GSearchResult:
    facet_results = None
    if "facet_results" in data:
        facet_results = [
            FacetResult(
                name=f["name"],
                value=f.get("value"),
                buckets=(
                    [FacetBucket(value=b["value"], count=b["count"]) for b in f["buckets"]]
                    if "buckets" in f
                    else None
                ),
            )
            for f in data["facet_results"]
        ]
    return GSearchResult(
        total=data["total"],
        count=data["count"],
        offset=data["offset"],
        has_next_page=data["has_next_page"],
        gmeta=[format_subject(r["subject"], r["entries"], only_fields) for r in data["gmeta"]],
        facet_results=facet_results,
    )


def globus_search_query(
    index_id: Annotated[str, Field(description="ID of the search index to query")],
    q: Annotated[
        str | None,
        Field(
            description=(
                "Query string. Required unless `filters` is given. By default it is parsed"
                " leniently; with `advanced` it supports field:value terms, AND/OR/NOT and"
                " parentheses, and a malformed query is an error."
            )
        ),
    ] = None,
    advanced: Annotated[
        bool, Field(description="Enable elasticsearch-style advanced query string syntax for `q`.")
    ] = False,
    filters: Annotated[
        list[Filter] | None,
        Field(description="Filters restricting the results. Applied before facets are counted."),
    ] = None,
    facets: Annotated[
        list[Facet] | None,
        Field(
            description="Aggregations (counts, histograms, sums) to compute. "
            "Use to summarize distinct values or categories."
        ),
    ] = None,
    post_facet_filters: Annotated[
        list[Filter] | None,
        Field(description="Filters applied to results only, after facet counts are computed."),
    ] = None,
    boosts: Annotated[
        list[Boost] | None,
        Field(description="Apply custom weights to change sort order. Ignored if `sort` is set."),
    ] = None,
    sort: Annotated[
        list[Sort] | None, Field(description="Explicit result ordering, instead of relevance.")
    ] = None,
    only_fields: OnlyFields = None,
    # Small page limits to avoid overwhelming LLM context
    limit: Annotated[int, Field(ge=1, le=50, description="Maximum results to return.")] = 10,
    offset: Annotated[int, Field(ge=0, description="Zero based offset into the result set.")] = 0,
    *,
    ctx: Context[GlobusContext],
) -> GSearchResult:
    """
    Query a Globus Search index and return records visible to the user.

    For advanced queries: nested fields are separated with `.`, eg `dc.title`.

    Result fields are index-specific. Search payloads may be big. To avoid overwhelming LLM context,
        always sample a few records first, then use the `only_fields` option to restrict
        result payload for all routine queries.

    See `globus_search_get_item` for single-item retrieval.
    """
    # Syntax ref: https://docs.globus.org/api/search/reference/post_query/#gboost
    client = get_search_client(ctx)
    body = _build_query_body(
        q=q,
        advanced=advanced,
        filters=filters,
        facets=facets,
        post_facet_filters=post_facet_filters,
        boosts=boosts,
        sort=sort,
    )
    try:
        r = client.post_search(index_id, body, limit=limit, offset=offset)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Search query failed: {e}") from e

    return _format_query_response(r.data, only_fields)
