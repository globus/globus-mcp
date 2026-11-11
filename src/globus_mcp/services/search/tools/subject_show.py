"""
Get the record for one single item by subject ID
"""

from typing import Annotated

import globus_sdk
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from globus_mcp.context import GlobusContext
from globus_mcp.services.search.client import get_search_client
from globus_mcp.services.search.schemas.gsearchresult import SearchSubject
from globus_mcp.services.search.util.field_selection import OnlyFields, format_subject


def globus_search_get_item(
    index_id: Annotated[str, Field(description="UUID of the search index")],
    subject_id: Annotated[str, Field(description="Subject ID")],
    only_fields: OnlyFields = None,
    *,
    ctx: Context[GlobusContext],
) -> SearchSubject:
    """
    Get one specific item (subject) from the search index, by provided ID.

    Search payloads may be big. To avoid overwhelming LLM context, use
        the `only_fields` option to restrict the result payload whenever possible.

    See `globus_search_query` for bulk queries and aggregations.
    """
    client = get_search_client(ctx)

    try:
        r = client.get_subject(index_id, subject_id)
    except globus_sdk.GlobusAPIError as e:
        # 404s need no special case: the API message says whether the subject or index is missing
        raise ToolError(
            f"Failed to get item {subject_id!r} from search index {index_id}: {e}"
        ) from e

    # A subject with no visible entries returns 200, not 403. From the MCP standpoint, this means
    #   "I can't answer your request, and I am offering guidance as to why".
    if not r["entries"]:
        raise ToolError(
            f"Item {subject_id!r} exists in search index {index_id}, but the user"
            f" does not have permission to see any of its entries."
        )

    return format_subject(r["subject"], r["entries"], only_fields)
