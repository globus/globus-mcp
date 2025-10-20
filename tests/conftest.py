from unittest.mock import Mock

import pytest
from mcp.server.fastmcp import Context

from globus_mcp.context import GlobusContext


@pytest.fixture
def mock_app():
    app = Mock()
    app.config.environment = "sandbox"
    return app


@pytest.fixture
def mock_ctx(mock_app: Mock):
    ctx = Mock(spec=Context)
    ctx.request_context.lifespan_context = GlobusContext(app=mock_app)
    return ctx
