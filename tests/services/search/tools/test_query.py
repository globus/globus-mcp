import pytest
from globus_sdk.testing import RegisteredResponse, load_response
from mcp.server.mcpserver.exceptions import ToolError

from globus_mcp.services.search.schemas.gsearchrequest import TermsFacet
from globus_mcp.services.search.schemas.gsearchresult import GSearchResult
from globus_mcp.services.search.tools.query import globus_search_query
from tests.utils import load_fixture, make_ctx

INDEX_ID = "00000000-0000-0000-0000-000000000000"


def _register(fixture: str, *, status: int = 200) -> None:
    load_response(
        RegisteredResponse(
            service="search",
            method="POST",
            path=f"/v1/index/{INDEX_ID}/search",
            json=load_fixture("search", fixture),
            status=status,
        )
    )


def test_query(search_client):
    _register("query.json")

    res = globus_search_query(INDEX_ID, q="*", limit=3, ctx=make_ctx(search_client=search_client))

    assert isinstance(res, GSearchResult)
    assert res.total == 1565402
    assert res.count == 3
    assert res.offset == 0
    assert res.has_next_page is True
    assert [s.subject for s in res.gmeta] == [
        "pubmed:34981557",
        "pubmed:34983422",
        "pubmed:34987792",
    ]
    assert all(len(s.entries) == 1 for s in res.gmeta)
    assert res.gmeta[0].entries[0].content["publisher"] == {"name": "Journal of food biochemistry"}
    # No facets were requested
    assert res.facet_results is None


def test_query_only_fields(search_client):
    _register("query.json")

    res = globus_search_query(
        INDEX_ID,
        q="*",
        only_fields=["publisher.name", "titles.title"],
        limit=3,
        ctx=make_ctx(search_client=search_client),
    )

    # Every subject is trimmed, and the nested structure is preserved
    source = load_fixture("search", "query.json")["gmeta"]
    assert len(res.gmeta) == 3
    for subject, raw in zip(res.gmeta, source, strict=True):
        raw_content = raw["entries"][0]["content"]
        assert subject.subject == raw["subject"]
        assert subject.entries[0].content == {
            "publisher": {"name": raw_content["publisher"]["name"]},
            "titles": raw_content["titles"],
        }


def test_query_index_not_found(search_client):
    _register("query_404_index.json", status=404)

    with pytest.raises(ToolError, match=r"Search query failed") as exc_info:
        globus_search_query(INDEX_ID, q="*", ctx=make_ctx(search_client=search_client))

    assert "NotFound.NoSuchIndex" in str(exc_info.value)
    assert "There is no search index named" in str(exc_info.value)


def test_query_with_facets(search_client):
    _register("query_with_facets.json")

    res = globus_search_query(
        INDEX_ID,
        q="*",
        facets=[
            TermsFacet(type="terms", name="publishers", field_name="publisher.name", size=5),
            TermsFacet(
                type="terms", name="publication_years", field_name="publicationYear", size=10
            ),
        ],
        limit=1,
        ctx=make_ctx(search_client=search_client),
    )

    assert isinstance(res, GSearchResult)
    assert res.total == 1565402
    assert res.count == 1
    assert res.has_next_page is True
    assert [s.subject for s in res.gmeta] == ["pubmed:34981557"]

    assert res.facet_results is not None
    facets = {f.name: f for f in res.facet_results}
    assert set(facets) == {"publishers", "publication_years"}

    publishers = facets["publishers"].buckets
    assert publishers is not None and len(publishers) == 5
    assert (publishers[0].value, publishers[0].count) == ("Journal of virology", 35373)

    years = facets["publication_years"].buckets
    assert years is not None and len(years) == 10
    assert (years[0].value, years[0].count) == ("2021", 133064)
