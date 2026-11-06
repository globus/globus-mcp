"""
Discover Globus Search indices where the user has a formally defined role

This tool is primarily useful when managing search indices,
    because it answers "what can I edit" rather than "what can I read"

(Any search index can be *queried*, even without authentication, and those will not be
    listed/searched using this tool)
"""

from typing import Annotated, Literal

import globus_sdk
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from globus_mcp.context import GlobusContext
from globus_mcp.services.search.client import get_search_client
from globus_mcp.services.search.schemas.gsearchindex import SearchIndex


def globus_search_list_my_indices(
    filter_roles: Annotated[
        list[Literal["owner", "admin", "writer"]] | None,
        Field(
            description=(
                "Only return indices on which the user holds at least one of these roles."
                " Omit (default) to return indices where the user has any role."
            ),
        ),
    ] = None,
    *,
    ctx: Context[GlobusContext],
) -> list[SearchIndex]:
    """
    List Globus Search indices on which the user has a role. (owner, admin, writer)

    Other search indices will not be shown in this list, even if the user can run queries there.
        Use `globus_search_show_index_details` to get metadata for just one index.
    """
    # TODO: This tool is disabled for now, because its mere existence forces the server
    #   to have elevated `search:all` scope. ("must be logged in, didn't fit a granular scope")
    #   Additionally, a notebook interface needs to answer "what can I query".
    #       (every search index supports anonymous queries...)
    #   This tool answers "what do I control", which is far more restrictive.
    client = get_search_client(ctx)

    try:
        # Impl NOTE: API has a hard limit of 100 items, no pagination.
        #  Almost no one will ever hit that limit in practice.
        r = client.index_list(filter_roles=filter_roles if filter_roles else globus_sdk.MISSING)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to list search indices: {e}") from e

    return [SearchIndex.from_payload(idx) for idx in r.data.get("index_list", [])]
