from unittest.mock import Mock

import pytest
from mcp.server.mcpserver import Context

from globus_mcp.context import GlobusContext
from tests.utils import random_string


@pytest.fixture
def mock_app():
    app = Mock()
    app.config.environment = "sandbox"
    app.get_client_retry_checks.return_value = []
    app.token_storage.identity_id = None
    return app


@pytest.fixture
def mock_ctx(mock_app: Mock):
    ctx = Mock(spec=Context)
    ctx.request_id = random_string()
    ctx.request_context.lifespan_context = GlobusContext(
        app=mock_app, server_session_id=random_string()
    )
    return ctx
