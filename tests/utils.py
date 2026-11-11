import json
import random
import string
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from globus_sdk import GlobusApp
from mcp.server.mcpserver import Context

from globus_mcp.context import GlobusContext

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def random_string(length: int = 10):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for _ in range(length))


def make_ctx(app: GlobusApp | None = None, **clients: Any) -> Mock:
    """
    Build a mock MCP `Context` wrapping a real `GlobusContext`.

    Pass pre-built clients by field name, eg `make_ctx(search_client=client)`.
    """
    ctx = Mock(spec=Context)
    ctx.request_context.lifespan_context = GlobusContext(app=app or Mock(), **clients)
    return ctx


def load_fixture(*parts: str) -> Any:
    """Load a JSON file from `tests/fixtures/`, eg `load_fixture("search", "index_show.json")`."""
    return json.loads(FIXTURES_DIR.joinpath(*parts).read_text())
