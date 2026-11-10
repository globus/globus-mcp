import pytest
from globus_sdk.testing import RegisteredResponse, load_response
from mcp.server.mcpserver.exceptions import ToolError

from globus_mcp.services.search.schemas.gsearchresult import SearchSubject
from globus_mcp.services.search.tools.subject_show import globus_search_get_item
from tests.utils import load_fixture, make_ctx

INDEX_ID = "00000000-0000-0000-0000-000000000000"
SUBJECT_ID = "pubmed:34981557"


def _register(fixture: str, *, status: int = 200) -> None:
    load_response(
        RegisteredResponse(
            service="search",
            method="GET",
            path=f"/v1/index/{INDEX_ID}/subject",
            json=load_fixture("search", fixture),
            status=status,
        )
    )


def test_get_item(search_client):
    _register("subject_show.json")

    res = globus_search_get_item(INDEX_ID, SUBJECT_ID, ctx=make_ctx(search_client=search_client))

    assert isinstance(res, SearchSubject)
    assert res.subject == SUBJECT_ID
    assert len(res.entries) == 1
    assert res.entries[0].entry_id is None
    # Full content is returned when `only_fields` is not given
    assert (
        res.entries[0].content
        == load_fixture("search", "subject_show.json")["entries"][0]["content"]
    )


def test_get_item_only_fields(search_client):
    _register("subject_show.json")

    res = globus_search_get_item(
        INDEX_ID,
        SUBJECT_ID,
        only_fields=["titles.title", "identifier.*"],
        ctx=make_ctx(search_client=search_client),
    )

    source = load_fixture("search", "subject_show.json")["entries"][0]["content"]
    assert res.subject == SUBJECT_ID
    assert res.entries[0].content == {
        "titles": source["titles"],
        "identifier": source["identifier"],
    }


def test_get_item_only_fields_no_match(search_client):
    # Unmatched patterns are ignored: the entry is returned, with empty content
    _register("subject_show.json")

    res = globus_search_get_item(
        INDEX_ID,
        SUBJECT_ID,
        only_fields=["no.such.field"],
        ctx=make_ctx(search_client=search_client),
    )

    assert len(res.entries) == 1
    assert res.entries[0].content == {}


def test_get_item_not_found(search_client):
    _register("subject_show_404_item.json", status=404)

    with pytest.raises(ToolError, match=r"Failed to get item") as exc_info:
        globus_search_get_item(INDEX_ID, "NO_SUCH_ITEM", ctx=make_ctx(search_client=search_client))

    # The API message identifies what is missing: here, the subject
    assert "NotFound.Generic" in str(exc_info.value)
    assert "Could not find metadata related to subject NO_SUCH_ITEM" in str(exc_info.value)


def test_get_item_index_not_found(search_client):
    _register("subject_show_404_index.json", status=404)

    with pytest.raises(ToolError, match=r"Failed to get item") as exc_info:
        globus_search_get_item(INDEX_ID, SUBJECT_ID, ctx=make_ctx(search_client=search_client))

    # The API message identifies what is missing: here, the index
    assert "NotFound.NoSuchIndex" in str(exc_info.value)
    assert "There is no search index named" in str(exc_info.value)


def test_get_item_no_visible_entries(search_client):
    # Search returns 200 with no entries for subjects the user is not allowed to see
    _register("subject_show_no_permissions.json")

    with pytest.raises(ToolError, match=r"does not have permission to see any of its entries") as e:
        globus_search_get_item(
            INDEX_ID, "DUMMY_INDEX_SEED", ctx=make_ctx(search_client=search_client)
        )

    assert "DUMMY_INDEX_SEED" in str(e.value)
    assert INDEX_ID in str(e.value)
