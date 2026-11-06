from collections.abc import Callable
from typing import Any

from globus_mcp.services.search.tools.index_show import globus_search_show_index_description

ALL_SEARCH_TOOLS: list[Callable[..., Any]] = [
    globus_search_show_index_description,
]
