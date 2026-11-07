from http import HTTPStatus

import globus_sdk
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from globus_mcp.context import GlobusContext
from globus_mcp.services.auth.client import get_auth_client
from globus_mcp.services.auth.schemas import WhoAmI


def _credentials_error_message(error: globus_sdk.GlobusAPIError, *, is_client: bool) -> str:
    """Explain a rejected credential in terms the user can act on."""
    if error.http_status == HTTPStatus.UNAUTHORIZED:
        if is_client:
            hint = "Invalid client credentials. Check GLOBUS_CLIENT_ID and GLOBUS_CLIENT_SECRET."
        else:
            hint = "Invalid user login. Restart the server to log in again."
        return f"HTTP 401: {hint}"

    return f"Failed to get identity information: {error}"


def globus_auth_userinfo(*, ctx: Context[GlobusContext]) -> WhoAmI:
    """
    Return the Globus identity that this MCP server is using to authenticate requests.

    Use this tool to verify that the intended user or service account is active, and to
    detect credential misconfigurations.
    """
    # This tool is always active, because it is used to introspect routine operations
    app = ctx.request_context.lifespan_context.app
    is_client = isinstance(app, globus_sdk.ClientApp)

    try:
        info = get_auth_client(ctx).userinfo()
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(_credentials_error_message(e, is_client=is_client)) from e

    return WhoAmI(
        identity_id=info["sub"],
        identity_type="client" if is_client else "user",
        username=info["preferred_username"],
        name=info["name"],
        identity_provider_display_name=info["identity_provider_display_name"],
        organization=info.get("organization"),
    )
