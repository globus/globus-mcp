import pytest
from globus_sdk.testing import RegisteredResponse, load_response
from mcp.server.mcpserver.exceptions import ToolError

from globus_mcp.services.search.schemas.gsearchindex import SearchIndex
from globus_mcp.services.search.tools.index_show import globus_search_show_index_description
from tests.utils import load_fixture, make_ctx

INDEX_ID = "00000000-0000-0000-0000-000000000000"


def _register(fixture: str, *, status: int = 200) -> None:
    load_response(
        RegisteredResponse(
            service="search",
            method="GET",
            path=f"/v1/index/{INDEX_ID}",
            json=load_fixture("search", fixture),
            status=status,
        )
    )


def test_show_index(search_client):
    _register("index_show.json")

    res = globus_search_show_index_description(INDEX_ID, ctx=make_ctx(search_client=search_client))

    assert isinstance(res, SearchIndex)
    assert res.index_id == "00000000-0000-0000-0000-000000000000"
    assert res.display_name == "Testing repository"
    assert res.description == "Sample data"
    assert res.size_in_mb == 11067
    assert res.num_subjects == 1565402
    assert res.num_entries == 1565402
    assert res.creation_date == "2026-03-31 13:34:52"
    assert res.content_last_modified_date == "2026-04-28 02:03:24"


def test_show_index_not_found(search_client):
    _register("index_show_404.json", status=404)

    with pytest.raises(ToolError, match=r"Failed to get details for search index") as exc_info:
        globus_search_show_index_description(INDEX_ID, ctx=make_ctx(search_client=search_client))

    assert INDEX_ID in str(exc_info.value)
    assert "NotFound.NoSuchIndex" in str(exc_info.value)
