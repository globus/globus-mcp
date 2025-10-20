import random
import uuid
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from globus_sdk import GlobusAPIError, IterableTransferResponse, TransferClient, TransferData
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from globus_mcp.context import GlobusContext
from globus_mcp.server import service_registry
from globus_mcp.services.transfer.client import get_transfer_client
from globus_mcp.services.transfer.registry import register_transfer
from globus_mcp.services.transfer.tools import (
    ALL_TRANSFER_TOOLS,
    _format_search_response,
    _handle_gare,
    globus_transfer_get_task_events,
    globus_transfer_list_directory,
    globus_transfer_list_endpoints_and_collections,
    globus_transfer_search_endpoints_and_collections,
    globus_transfer_submit_task,
)
from tests.utils import random_string


@pytest.fixture
def mock_client():
    with patch("globus_mcp.services.transfer.tools.get_transfer_client") as mock_get_client:
        mc = Mock(spec=TransferClient)
        mock_get_client.return_value = mc
        yield mc


@pytest.fixture
def mock_handle_gare():
    with patch("globus_mcp.services.transfer.tools._handle_gare") as _mock_handle_gare:
        yield _mock_handle_gare


@pytest.fixture
def mock_format_search_res():
    with patch("globus_mcp.services.transfer.tools._format_search_response") as _format_search_res:
        yield _format_search_res


def test_transfer_in_service_registry():
    assert "transfer" in service_registry
    assert service_registry["transfer"] is register_transfer


def test_register_transfer():
    mcp = Mock(spec=FastMCP)
    register_transfer(mcp)
    registered = [c[0][0] for c in mcp.add_tool.call_args_list]
    for tool in ALL_TRANSFER_TOOLS:
        assert tool in registered


def test_get_transfer_client(mock_ctx: Mock):
    globus_ctx: GlobusContext = mock_ctx.request_context.lifespan_context
    globus_ctx.app.app_name = random_string()
    assert globus_ctx.transfer_client is None, "Ensure setup"

    client = get_transfer_client(mock_ctx)
    assert globus_ctx.transfer_client is client
    assert isinstance(client, TransferClient)
    assert client.app_name == globus_ctx.app.app_name

    client_2 = get_transfer_client(mock_ctx)
    assert client_2 is client, "Client should be cached"


def test_handle_gare_happy_path(mock_client: Mock):
    res_data = random_string()
    mock_client.some_method = Mock()
    mock_client.some_method.return_value = res_data
    mock_client.some_method.__self__ = mock_client

    args = [random_string() for _ in range(random.randint(1, 10))]
    kwargs = {random_string(): random_string() for _ in range(random.randint(1, 10))}
    res = _handle_gare(mock_client.some_method, *args, **kwargs)

    assert res == res_data
    mock_client.some_method.assert_called_once_with(*args, **kwargs)


def test_handle_gare_consent_required(mock_client: Mock):
    error = GlobusAPIError(r=MagicMock())
    error.http_status = HTTPStatus.FORBIDDEN
    error.code = "ConsentRequired"
    required_scopes = [random_string() for _ in range(random.randint(1, 10))]
    error.info.consent_required.required_scopes = required_scopes

    res_data = random_string()
    mock_client.some_method = Mock()
    mock_client.some_method.side_effect = [error, res_data]
    mock_client.some_method.__self__ = mock_client

    args = [random_string() for _ in range(random.randint(1, 10))]
    kwargs = {random_string(): random_string() for _ in range(random.randint(1, 10))}
    res = _handle_gare(mock_client.some_method, *args, **kwargs)

    assert res == res_data
    assert mock_client.some_method.call_count == 2
    mock_client.some_method.assert_called_with(*args, **kwargs)
    added_scopes = [s[0][0] for s in mock_client.add_app_scope.call_args_list]
    for scope in required_scopes:
        assert scope in added_scopes


def test_handle_gare_unexpected_error(mock_client: Mock):
    error = GlobusAPIError(r=MagicMock())
    error.http_status = HTTPStatus.INTERNAL_SERVER_ERROR

    mock_client.some_method = Mock()
    mock_client.some_method.side_effect = error
    mock_client.some_method.__self__ = mock_client

    with pytest.raises(GlobusAPIError):
        _handle_gare(mock_client.some_method)


def test_format_search_response():
    res_data: dict[str, Any] = {
        "limit": random.randint(1, 1000),
        "offset": random.randint(0, 1000),
        "has_next_page": False,
        "DATA": [],
    }
    for _ in range(random.randint(1, 10)):
        res_data["DATA"].append(
            {
                "id": str(uuid.uuid4()),
                "display_name": random_string(),
                "owner_id": str(uuid.uuid4()),
                "owner_string": random_string(),
                "entity_type": random_string(),
                "description": random_string(),
            }
        )

    mock_res = Mock(spec=IterableTransferResponse)
    mock_res.__getitem__ = Mock(side_effect=lambda k: res_data[k])
    mock_res.get = Mock(side_effect=lambda k, d=None: res_data.get(k, d))
    mock_res.__iter__ = Mock(return_value=iter(res_data["DATA"]))

    res = _format_search_response(mock_res)

    assert res.limit == res_data["limit"]
    assert res.offset == res_data["offset"]
    assert res.has_next_page == res_data["has_next_page"]
    for idx, ep in enumerate(res.data):
        ep_data = res_data["DATA"][idx]
        assert ep.endpoint_id == ep_data["id"]
        assert ep.display_name == ep_data["display_name"]
        assert ep.owner_id == ep_data["owner_id"]
        assert ep.owner_string == ep_data["owner_string"]
        assert ep.type == ep_data["entity_type"]
        assert ep.description == ep_data["description"]


def test_globus_transfer_list_endpoints_and_collections(
    mock_ctx: Mock, mock_client: Mock, mock_format_search_res: Mock
):
    limit = random.randint(1, 100)
    offset = random.randint(0, 100)

    search_res = Mock()
    formatted_res = Mock()
    mock_client.endpoint_search.return_value = search_res
    mock_format_search_res.return_value = formatted_res

    filter_scope = random_string()
    res = globus_transfer_list_endpoints_and_collections(
        filter_scope=filter_scope,
        limit=limit,
        offset=offset,
        ctx=mock_ctx,
    )

    mock_client.endpoint_search.assert_called_once_with(
        filter_scope=filter_scope,
        limit=limit,
        offset=offset,
    )
    mock_format_search_res.assert_called_once_with(search_res)
    assert res == formatted_res


def test_globus_transfer_list_endpoints_and_collections_api_error(
    mock_ctx: Mock, mock_client: Mock
):
    mock_client.endpoint_search.side_effect = GlobusAPIError(r=MagicMock())
    with pytest.raises(ToolError, match="Failed to get search results"):
        globus_transfer_list_endpoints_and_collections(
            filter_scope=random_string(),
            limit=100,
            offset=0,
            ctx=mock_ctx,
        )


def test_globus_transfer_search_endpoints_and_collections(
    mock_ctx: Mock, mock_client: Mock, mock_format_search_res: Mock
):
    limit = random.randint(1, 100)
    offset = random.randint(0, 100)

    search_res = Mock()
    formatted_res = Mock()
    mock_client.endpoint_search.return_value = search_res
    mock_format_search_res.return_value = formatted_res

    filter_fulltext = random_string()
    res = globus_transfer_search_endpoints_and_collections(
        filter_fulltext=filter_fulltext,
        limit=limit,
        offset=offset,
        ctx=mock_ctx,
    )

    mock_client.endpoint_search.assert_called_once_with(
        filter_scope="all",
        filter_fulltext=filter_fulltext,
        limit=limit,
        offset=offset,
    )
    mock_format_search_res.assert_called_once_with(search_res)
    assert res == formatted_res


def test_globus_transfer_search_endpoints_and_collections_api_error(
    mock_ctx: Mock, mock_client: Mock
):
    mock_client.endpoint_search.side_effect = GlobusAPIError(r=MagicMock())
    with pytest.raises(ToolError, match="Failed to get search results"):
        globus_transfer_search_endpoints_and_collections(
            filter_fulltext=random_string(),
            limit=100,
            offset=0,
            ctx=mock_ctx,
        )


def test_globus_transfer_submit_task(mock_ctx: Mock, mock_client: Mock, mock_handle_gare: Mock):
    source_collection_id = str(uuid.uuid4())
    destination_collection_id = str(uuid.uuid4())
    source_path = random_string()
    destination_path = random_string()
    label = random_string()
    task_id = str(uuid.uuid4())

    transfer_data = TransferData(
        source_endpoint=source_collection_id,
        destination_endpoint=destination_collection_id,
        label=label,
    )
    transfer_data.add_item(source_path=source_path, destination_path=destination_path)

    mock_handle_gare.return_value = Mock(data={"task_id": task_id})

    res = globus_transfer_submit_task(
        source_collection_id=source_collection_id,
        destination_collection_id=destination_collection_id,
        source_path=source_path,
        destination_path=destination_path,
        label=label,
        ctx=mock_ctx,
    )

    mock_handle_gare.assert_called_once_with(mock_client.submit_transfer, transfer_data)
    assert res.task_id == task_id


def test_globus_transfer_submit_task_api_error(mock_ctx: Mock, mock_handle_gare: Mock):
    mock_handle_gare.side_effect = GlobusAPIError(r=MagicMock())
    with pytest.raises(ToolError, match="Failed to submit transfer"):
        globus_transfer_submit_task(
            source_collection_id=str(uuid.uuid4()),
            destination_collection_id=str(uuid.uuid4()),
            source_path=random_string(),
            destination_path=random_string(),
            label=random_string(),
            ctx=mock_ctx,
        )


def test_globus_transfer_get_task_events(mock_ctx: Mock, mock_client: Mock):
    task_id = str(uuid.uuid4())

    res_data: dict[str, Any] = {
        "limit": random.randint(1, 1000),
        "offset": random.randint(0, 1000),
        "DATA": [],
    }
    for _ in range(random.randint(1, 10)):
        res_data["DATA"].append(
            {
                "code": random_string(),
                "is_error": False,
                "description": random_string(),
                "details": random_string(),
                "time": random_string(),
            }
        )
    mock_client.task_event_list.return_value = res_data

    res = globus_transfer_get_task_events(
        task_id=task_id, limit=res_data["limit"], offset=res_data["offset"], ctx=mock_ctx
    )

    mock_client.task_event_list.assert_called_once_with(
        task_id=task_id, limit=res_data["limit"], offset=res_data["offset"]
    )
    assert res.limit == res_data["limit"]
    assert res.offset == res_data["offset"]
    for idx, event in enumerate(res.data):
        event_data = res_data["DATA"][idx]
        assert event.code == event_data["code"]
        assert event.is_error is event_data["is_error"]
        assert event.description == event_data["description"]
        assert event.details == event_data["details"]
        assert event.time == event_data["time"]


def test_globus_transfer_get_task_events_api_error(mock_ctx: Mock, mock_client: Mock):
    mock_client.task_event_list.side_effect = GlobusAPIError(r=MagicMock())
    with pytest.raises(ToolError, match="Failed to get task events"):
        globus_transfer_get_task_events(task_id=str(uuid.uuid4()), limit=10, offset=0, ctx=mock_ctx)


def test_globus_transfer_list_directory(mock_ctx: Mock, mock_client: Mock):
    collection_id = str(uuid.uuid4())
    path = random_string()

    res_data: dict[str, Any] = {
        "limit": random.randint(1, 1000),
        "offset": random.randint(0, 1000),
        "DATA": [],
    }
    for _ in range(random.randint(1, 10)):
        res_data["DATA"].append(
            {
                "name": random_string(),
                "type": random_string(),
                "link_target": random_string(),
                "user": random_string(),
                "group": random_string(),
                "permissions": random_string(),
                "size": random.randint(1, 1000),
                "last_modified": random_string(),
            }
        )
    mock_client.operation_ls.return_value = res_data

    res = globus_transfer_list_directory(
        collection_id=collection_id,
        path=path,
        limit=res_data["limit"],
        offset=res_data["offset"],
        ctx=mock_ctx,
    )

    mock_client.operation_ls.assert_called_once_with(
        collection_id, path=path, limit=res_data["limit"], offset=res_data["offset"]
    )
    assert res.limit == res_data["limit"]
    assert res.offset == res_data["offset"]
    for idx, file in enumerate(res.data):
        file_data = res_data["DATA"][idx]
        assert file.name == file_data["name"]
        assert file.type == file_data["type"]
        assert file.link_target == file_data["link_target"]
        assert file.user == file_data["user"]
        assert file.group == file_data["group"]
        assert file.permissions == file_data["permissions"]
        assert file.size == file_data["size"]
        assert file.last_modified == file_data["last_modified"]


def test_globus_transfer_list_directory_api_error(mock_ctx: Mock, mock_client: Mock):
    mock_client.operation_ls.side_effect = GlobusAPIError(r=MagicMock())
    with pytest.raises(ToolError, match="Failed to list directory contents"):
        globus_transfer_list_directory(
            collection_id=str(uuid.uuid4()), path=random_string(), limit=100, offset=0, ctx=mock_ctx
        )
