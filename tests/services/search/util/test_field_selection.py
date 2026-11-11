from typing import Any

import pytest

from globus_mcp.services.search.util.field_selection import compile_field_patterns, select_fields

CONTENT: dict[str, Any] = {
    "dc": {
        "titles": [{"title": "T", "lang": "en"}, {"title": "U"}],
        "publisher": "P",
    },
    "files": [{"url": "u", "md5": "m"}, {"url": "v"}],
    "a.b": 1,
    "x": {"b": 2},
}


def _select(*patterns: str, content: dict[str, Any] = CONTENT) -> dict[str, Any]:
    return select_fields(content, compile_field_patterns(list(patterns)))


def test_nested_path_preserves_structure():
    assert _select("dc.publisher") == {"dc": {"publisher": "P"}}


def test_multiple_patterns_are_unioned():
    assert _select("dc.publisher", "x.b") == {"dc": {"publisher": "P"}, "x": {"b": 2}}


def test_path_into_list_applies_to_each_element():
    assert _select("files.url") == {"files": [{"url": "u"}, {"url": "v"}]}


def test_list_elements_without_match_are_dropped():
    assert _select("dc.titles.lang") == {"dc": {"titles": [{"lang": "en"}]}}


def test_selecting_object_returns_whole_subtree():
    assert _select("dc") == {"dc": CONTENT["dc"]}


def test_selecting_list_returns_whole_list():
    assert _select("files") == {"files": CONTENT["files"]}


def test_trailing_wildcard_equivalent_to_prefix():
    assert _select("dc.*") == _select("dc")


def test_wildcard_in_middle_segment():
    assert _select("dc.*.title") == {"dc": {"titles": [{"title": "T"}, {"title": "U"}]}}


def test_leading_wildcard_matches_any_depth():
    assert _select("*.b") == {"a.b": 1, "x": {"b": 2}}


def test_missing_path_ignored():
    assert _select("nope", "dc.nope.deeper", "dc.publisher") == {"dc": {"publisher": "P"}}


def test_no_matches_yields_empty_content():
    assert _select("nope") == {}


def test_literal_dotted_key_matched_by_full_path():
    assert _select("a.b") == {"a.b": 1}


def test_partial_segment_does_not_match():
    assert _select("d") == {}
    assert _select("dc.pub") == {}


@pytest.mark.parametrize("pattern", ["dc.?ublisher", "dc.[p]ublisher", "dc.publisher|x"])
def test_only_star_is_special(pattern: str):
    assert _select(pattern) == {}


def test_empty_content():
    assert _select("dc", content={}) == {}


def test_falsy_values_are_kept_when_selected():
    content = {"n": 0, "s": "", "b": False, "l": [], "d": {}, "z": None}
    assert _select("n", "s", "b", "l", "d", "z", content=content) == content
