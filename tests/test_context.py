from unittest.mock import Mock, patch

import pytest
from globus_sdk import UserApp
from mcp.server.fastmcp import FastMCP

from globus_mcp.context import GlobusContext, lifespan


@pytest.mark.asyncio
async def test_lifespan_yields_globus_context():
    mock_app = Mock(spec=UserApp)
    mock_server = Mock(spec=FastMCP)

    with patch("globus_mcp.context.get_globus_app", return_value=mock_app):
        async with lifespan(mock_server) as context:
            assert isinstance(context, GlobusContext)
            assert context.app is mock_app
            assert context.transfer_client is None
            assert context.compute_client is None
