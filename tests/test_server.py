from unittest.mock import Mock, patch

import pytest

from globus_mcp.server import main, mcp, services
from tests.utils import random_string


@patch.object(mcp, "run")
def test_run_server_default(mock_mcp_run: Mock):
    with patch.dict(
        "globus_mcp.server.service_registry", {s: Mock() for s in services}
    ) as service_registry:
        with patch("sys.argv", ["globus-mcp"]):
            main()
            for service in services:
                service_registry[service].assert_called_once_with(mcp)
            mock_mcp_run.assert_called_once_with(transport="stdio")


@patch.object(mcp, "run")
@pytest.mark.parametrize("registered", [services[: i + 1] for i in range(len(services))])
def test_run_server_with_select_services(mock_mcp_run: Mock, registered: list[str]):
    with patch.dict(
        "globus_mcp.server.service_registry", {s: Mock() for s in services}
    ) as service_registry:
        args = ["globus-mcp", "--services"] + registered
        with patch("sys.argv", args):
            main()

            for service in registered:
                service_registry[service].assert_called_once_with(mcp)

            unregistered = set(services) - set(registered)
            for service in unregistered:
                service_registry[service].assert_not_called()

            mock_mcp_run.assert_called_once_with(transport="stdio")


@patch.object(mcp, "run")
def test_run_server_with_invalid_service(mock_mcp_run: Mock):
    args = ["globus-mcp", "--services", random_string()]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # argparse error exit code
        mock_mcp_run.assert_not_called()
