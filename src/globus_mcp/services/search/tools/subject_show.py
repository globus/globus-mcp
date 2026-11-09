"""
Get the record for one single item by subject/entry ID
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

    Search payloads may be big. To avoid overwhelming LLM context, consider using
        the `only_fields` option to restrict the result payload.

    See `globus_search_query` for bulk queries and aggregations.
    """
    client = get_search_client(ctx)

    try:
        r = client.get_subject(index_id, subject_id)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(
            f"Failed to get item {subject_id!r} from search index {index_id}: {e}"
        ) from e

    return format_subject(r["subject"], r["entries"], only_fields)
