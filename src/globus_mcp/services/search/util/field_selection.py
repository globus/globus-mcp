"""
Client-side field selection for search entry content.

Globus Search cannot limit which fields come back in a response, so we trim `content` after
the fact to keep the LLM's context small. Syntax inspired by elasticsearch `_source` includes:

- A pattern is a dotted path into nested objects, eg `dc.titles.title`.
- `*` matches any run of characters (including `.`), so `dc.*` selects everything under `dc`.
  No other wildcard syntax is supported.
- A pattern that matches an object or list selects its whole subtree, so `dc` and `dc.*`
  are equivalent for that purpose.
- Lists are transparent: a path into a list of objects applies to every element.
- Patterns matching nothing are ignored, not an error.

Keys that literally contain a `.` (not nested) are matched by their full path string, so
`{"a.b": 1}` and `{"a": {"b": 1}}` are both selected by the pattern `a.b`.
"""

import re
from typing import Annotated, Any

from pydantic import Field

from globus_mcp.services.search.schemas.gsearchresult import SearchEntry, SearchSubject

# Shared by every tool that offers client-side field selection
OnlyFields = Annotated[
    list[str] | None,
    Field(
        min_length=1,
        description=(
            "Optionally limit each result to these fields, to keep responses small."
            " Syntax: Dotted paths into nested objects, eg `dc.titles.title`; `*` is wildcard,"
            " eg `dc.*`. Selecting an object returns everything under it. Paths that match"
            " nothing are ignored, so an entry with none of these fields comes back empty: "
            " re-request with different or more fields."
        ),
    ),
]

_MISSING = object()


def compile_field_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    """Compile `*`-wildcard path patterns. Everything other than `*` is matched literally."""
    return [re.compile(".*".join(re.escape(part) for part in p.split("*"))) for p in patterns]


def _select(value: Any, path: str, patterns: list[re.Pattern[str]]) -> Any:
    if path and any(p.fullmatch(path) for p in patterns):
        return value  # selected: keep the whole subtree

    if isinstance(value, dict):
        out = {}
        for key, child in value.items():
            selected = _select(child, f"{path}.{key}" if path else str(key), patterns)
            if selected is not _MISSING:
                out[key] = selected
        return out if out else _MISSING

    if isinstance(value, list):
        # Indices are not part of the path: each element is tested against the same path
        items = [
            selected
            for item in value
            if (selected := _select(item, path, patterns)) is not _MISSING
        ]
        return items if items else _MISSING

    return _MISSING


def select_fields(content: dict[str, Any], patterns: list[re.Pattern[str]]) -> dict[str, Any]:
    """
    Return only the parts of `content` whose path matches one of the compiled `patterns`.

    The nested structure of the original is preserved. If nothing matches, the result is an
    empty dict.
    """
    selected = _select(content, "", patterns)
    return {} if selected is _MISSING else selected


def format_subject(
    subject: str, entries: list[dict[str, Any]], only_fields: list[str] | None = None
) -> SearchSubject:
    """
    Build a `SearchSubject` from raw Search entries (dicts with `entry_id` and `content`),
    optionally trimming each entry's `content` to `only_fields`.
    """
    patterns = compile_field_patterns(only_fields) if only_fields else None
    return SearchSubject(
        subject=subject,
        entries=[
            SearchEntry(
                entry_id=e.get("entry_id"),
                content=(
                    e["content"] if patterns is None else select_fields(e["content"], patterns)
                ),
            )
            for e in entries
        ],
    )
