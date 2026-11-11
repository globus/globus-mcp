from collections.abc import Callable
from typing import Any

from globus_mcp.services.search.tools.index_show import globus_search_show_index_description
from globus_mcp.services.search.tools.query import globus_search_query
from globus_mcp.services.search.tools.subject_show import globus_search_get_item

ALL_SEARCH_TOOLS: list[Callable[..., Any]] = [
    globus_search_show_index_description,
    globus_search_query,
    globus_search_get_item,
]
