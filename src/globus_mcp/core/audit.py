"""
Helpers for structured audit logging
"""

import functools
import json
import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TextIO

import globus_sdk
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from globus_mcp.context import GlobusContext

_LOGGER_NAME = "globus_mcp.audit"
_EXTRA_FIELDS = (
    "request_id",
    "server_session_id",
    "tool_name",
    "service",
    "globus_identity",
    "client_name",
    "client_version",
    "error_type",
    "error_message",
    "error_body",
)

audit_logger = logging.getLogger(_LOGGER_NAME)


class _JsonlFormatter(logging.Formatter):
    """All events are output as structured JSONL with specified fields"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="microseconds"
            ),
            "level": record.levelname,
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        result: dict[str, Any] | None = getattr(record, "result", None)
        if result:
            payload["output"] = result
        return json.dumps(payload)


def configure_audit_logging(stream: TextIO = sys.stderr) -> None:
    """
    Attach a JSONL stream handler to stderr (stdout is reserved for MCP transport).
    """
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_JsonlFormatter())

    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False

    # Core `MCPServer` configures a string-based logger. Reconfigure it to use JSONL
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_globus_identity(ctx: Context[GlobusContext]) -> str | None:
    """
    Capture the globus user used to perform a remote action.

    A ClientApp (service credentials) never receives an id_token,
        but in that case `client_id` is the identity directly.
    """
    app = ctx.request_context.lifespan_context.app
    identity_id = app.token_storage.identity_id
    if identity_id is None and isinstance(app, globus_sdk.ClientApp):
        return str(app.client_id)
    return identity_id


def get_harness_identity(ctx: Context[GlobusContext]) -> tuple[str | None, str | None]:
    """If a client (harness) identifies itself, capture which agent performed the action"""
    client_params = ctx.session.client_params
    if client_params is None:
        return None, None
    client_info = client_params.client_info
    return client_info.name, client_info.version


def _base_extra(
    ctx: Context[GlobusContext],
    *,
    event: str,
    tool_name: str,
    service: str,
    include_globus_identity: bool,
) -> dict[str, Any]:
    client_name, client_version = get_harness_identity(ctx)
    return {
        "event": event,
        "request_id": ctx.request_id,
        "server_session_id": ctx.request_context.lifespan_context.server_session_id,
        "tool_name": tool_name,
        "service": service,
        "globus_identity": get_globus_identity(ctx) if include_globus_identity else None,
        "client_name": client_name,
        "client_version": client_version,
    }


def log_tool_call(
    ctx: Context[GlobusContext],
    *,
    tool_name: str,
    service: str,
    include_globus_identity: bool = True,  # True if tool calls an external Globus service
) -> None:
    audit_logger.info(
        f"Tool call: {tool_name}",
        extra=_base_extra(
            ctx,
            event="tool_call",
            tool_name=tool_name,
            service=service,
            include_globus_identity=include_globus_identity,
        ),
    )


def log_tool_result(
    ctx: Context[GlobusContext],
    *,
    tool_name: str,
    service: str,
    result: dict[str, Any],
    include_globus_identity: bool = True,
) -> None:
    extra = _base_extra(
        ctx,
        event="tool_result",
        tool_name=tool_name,
        service=service,
        include_globus_identity=include_globus_identity,
    )
    extra["result"] = result
    audit_logger.info(f"Tool result: {tool_name}", extra=extra)


def log_tool_error(
    ctx: Context[GlobusContext],
    *,
    tool_name: str,
    service: str,
    error: BaseException,
    include_globus_identity: bool = True,
) -> None:
    extra = _base_extra(
        ctx,
        event="tool_error",
        tool_name=tool_name,
        service=service,
        include_globus_identity=include_globus_identity,
    )
    extra["error_type"] = type(error).__name__
    extra["error_message"] = str(error)
    if isinstance(error, globus_sdk.GlobusAPIError):
        # Full verbatim response body; includes structured details (eg GARE) for troubleshooting
        extra["error_body"] = error.text
    audit_logger.error(f"Tool error in {tool_name}: {error}", extra=extra)


def _root_cause(error: BaseException) -> BaseException:
    """The innermost exception in a `raise ... from` chain (the error, if it has no cause)."""
    seen = {id(error)}
    while error.__cause__ is not None and id(error.__cause__) not in seen:
        error = error.__cause__
        seen.add(id(error))
    return error


def audited(
    service: str, *, include_globus_identity: bool = True
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Tool decorator: Log all tool calls (and errors)

    Requires access to server context as named argument `ctx`

    Tool results are tool-specific, and not captured by this decorator.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = kwargs["ctx"]
            log_tool_call(
                ctx,
                tool_name=tool_name,
                service=service,
                include_globus_identity=include_globus_identity,
            )
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                log_tool_error(
                    ctx,
                    tool_name=tool_name,
                    service=service,
                    error=_root_cause(e),
                    include_globus_identity=include_globus_identity,
                )
                if isinstance(e, ToolError):
                    raise
                raise ToolError(
                    f"Unexpected error in {tool_name}. Details are in the server audit log."
                ) from e

        return wrapper

    return decorator
