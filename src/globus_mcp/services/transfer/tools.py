from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any, Literal

import globus_sdk
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.session import ServerSession
from pydantic import Field

from globus_mcp.context import GlobusContext
from globus_mcp.services.transfer.client import get_transfer_client
from globus_mcp.services.transfer.schemas import (
    TransferEndpoint,
    TransferEndpointList,
    TransferEvent,
    TransferEventList,
    TransferFile,
    TransferFileList,
    TransferSubmitResponse,
)


def _handle_gare(
    client_method: Callable[..., globus_sdk.GlobusHTTPResponse],
    *args: Any,
    **kwargs: Any,
) -> globus_sdk.GlobusHTTPResponse:
    client: globus_sdk.TransferClient = client_method.__self__  # type: ignore[attr-defined]
    try:
        return client_method(*args, **kwargs)
    except globus_sdk.GlobusAPIError as e:
        if e.http_status == HTTPStatus.FORBIDDEN and e.code == "ConsentRequired":
            scopes = e.info.consent_required.required_scopes
            for scope in scopes:
                client.add_app_scope(scope)
            return client_method(*args, **kwargs)
        raise


def _format_search_response(res: globus_sdk.IterableTransferResponse) -> TransferEndpointList:
    endpoints = []
    for e in res["DATA"]:
        endpoint = TransferEndpoint(
            endpoint_id=e["id"],
            display_name=e["display_name"],
            owner_id=e["owner_id"],
            owner_string=e["owner_string"],
            type=e["entity_type"],
            description=e.get("description"),
        )
        endpoints.append(endpoint)
    return TransferEndpointList(
        limit=res["limit"],
        offset=res["offset"],
        has_next_page=res["has_next_page"],
        data=endpoints,
    )


def globus_transfer_list_endpoints_and_collections(
    filter_scope: Annotated[
        Literal[
            "my-endpoints",
            "administered-by-me",
            "shared-with-me",
            "shared-by-me",
            "recently-used",
            "in-use",
        ],
        Field(
            description=(
                "String indicating which scope/class of endpoints and collections to list."
                " Options:"
                " my-endpoints (owned by the user),"
                " administered-by-me (user has admin role, superset of my-endpoints),"
                " shared-with-me (shared with user),"
                " shared-by-me (guest collections where user is admin or access manager),"
                " recently-used (recently used by user),"
                " in-use (with active tasks owned by user),"
            ),
        ),
    ],
    limit: Annotated[
        int, Field(default=100, le=100, description="Maximum number of results to return.")
    ],
    offset: Annotated[int, Field(default=0, description="Zero based offset into the result set.")],
    ctx: Context[ServerSession, GlobusContext],
) -> TransferEndpointList:
    """List Globus Transfer endpoints and collections that the user has access to, filtered based
    on the provided scope.
    """
    client = get_transfer_client(ctx)

    try:
        res = client.endpoint_search(
            filter_scope=filter_scope,
            limit=limit,
            offset=offset,
        )
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to get search results: {e}") from e

    return _format_search_response(res)


def globus_transfer_search_endpoints_and_collections(
    filter_fulltext: Annotated[
        str,
        Field(ge=1, description=("String to match endpoint fields against.")),
    ],
    limit: Annotated[
        int, Field(default=100, le=100, description="Maximum number of results to return.")
    ],
    offset: Annotated[int, Field(default=0, description="Zero based offset into the result set.")],
    ctx: Context[ServerSession, GlobusContext],
) -> TransferEndpointList:
    """Use a filter string to search all Globus Transfer endpoints and collections that
    are visible to the user.
    """
    client = get_transfer_client(ctx)

    try:
        res = client.endpoint_search(
            filter_scope="all",
            filter_fulltext=filter_fulltext,
            limit=limit,
            offset=offset,
        )
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to get search results: {e}") from e

    return _format_search_response(res)


def globus_transfer_submit_task(
    source_collection_id: Annotated[str, Field(description="ID of the source collection")],
    destination_collection_id: Annotated[
        str, Field(description="ID of the destination collection")
    ],
    source_path: Annotated[
        str, Field(description="Path to the source directory or file of the transfer")
    ],
    destination_path: Annotated[
        str,
        Field(description="Path to the destination directory or file of the transfer"),
    ],
    label: Annotated[
        str,
        Field(default="Globus MCP Transfer", description="Label for the transfer task"),
    ],
    ctx: Context[ServerSession, GlobusContext],
) -> TransferSubmitResponse:
    """Submit a transfer task between two Globus Transfer collections.

    Use globus_transfer_get_task_events to monitor the task's progress.
    """
    client = get_transfer_client(ctx)

    data = globus_sdk.TransferData(
        source_endpoint=source_collection_id,
        destination_endpoint=destination_collection_id,
        label=label,
    )
    data.add_item(source_path=source_path, destination_path=destination_path)

    try:
        res = _handle_gare(client.submit_transfer, data)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to submit transfer: {e}") from e

    return TransferSubmitResponse(task_id=res.data["task_id"])


def globus_transfer_get_task_events(
    task_id: Annotated[str, Field(description="ID of the task")],
    limit: Annotated[
        int, Field(default=10, le=1_000, description="Maximum number of results to return.")
    ],
    offset: Annotated[int, Field(default=0, description="Zero based offset into the result set.")],
    ctx: Context[ServerSession, GlobusContext],
) -> TransferEventList:
    """Get a list of Globus Transfer task events to monitor the status and progress of a task.
    The events are ordered by time descending (newest first).
    """
    client = get_transfer_client(ctx)

    try:
        res = client.task_event_list(task_id=task_id, limit=limit, offset=offset)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to get task events: {e}") from e

    events = []
    for ev in res["DATA"]:
        event = TransferEvent(
            code=ev["code"],
            is_error=ev["is_error"],
            description=ev["description"],
            details=ev["details"],
            time=ev["time"],
        )
        events.append(event)

    return TransferEventList(limit=res["limit"], offset=res["offset"], data=events)


def globus_transfer_list_directory(
    collection_id: Annotated[str, Field(description="ID of the collection")],
    path: Annotated[str, Field(description="Path to a directory")],
    limit: Annotated[
        int, Field(default=100, le=100_000, description="Maximum number of results to return.")
    ],
    offset: Annotated[int, Field(default=0, description="Zero based offset into the result set.")],
    ctx: Context[ServerSession, GlobusContext],
) -> TransferFileList:
    """List contents of a directory on a Globus Transfer collection"""
    client = get_transfer_client(ctx)

    try:
        res = client.operation_ls(collection_id, path=path, limit=limit, offset=offset)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to list directory contents: {e}") from e

    files = []
    for f in res["DATA"]:
        file = TransferFile(
            name=f["name"],
            type=f["type"],
            link_target=f.get("link_target"),
            user=f.get("user"),
            group=f.get("group"),
            permissions=f["permissions"],
            size=f["size"],
            last_modified=f["last_modified"],
        )
        files.append(file)

    return TransferFileList(limit=limit, offset=offset, data=files)


ALL_TRANSFER_TOOLS: list[Callable[..., Any]] = [
    globus_transfer_search_endpoints_and_collections,
    globus_transfer_list_endpoints_and_collections,
    globus_transfer_submit_task,
    globus_transfer_get_task_events,
    globus_transfer_list_directory,
]
