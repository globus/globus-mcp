"""
Fetch metadata for a(ny) single Globus Search index
"""

from typing import Annotated

import globus_sdk
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from globus_mcp.context import GlobusContext
from globus_mcp.services.search.client import get_search_client
from globus_mcp.services.search.schemas.gsearchindex import SearchIndex


def globus_search_show_index_description(
    index_id: Annotated[str, Field(description="UUID of the search index")],
    *,
    ctx: Context[GlobusContext],
) -> SearchIndex:
    """
    Describe any one Globus Search index (a set of searchable items).
    """
    client = get_search_client(ctx)

    try:
        r = client.get_index(index_id)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to get details for search index {index_id!r}: {e}") from e

    return SearchIndex.from_payload(r.data)
