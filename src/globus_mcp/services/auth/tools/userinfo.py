import globus_sdk
from mcp.server.mcpserver import Context

from globus_mcp.context import GlobusContext
from globus_mcp.services.auth.client import get_auth_client
from globus_mcp.services.auth.schemas import WhoAmI


def globus_auth_userinfo(*, ctx: Context[GlobusContext]) -> WhoAmI:
    """
    Return the Globus identity that this MCP server is using to authenticate requests.

    Use this tool to verify that the intended user or service account is active, and to
    detect credential misconfigurations.
    """
    # This tool is always active, because it is used to introspect routine operations
    app = ctx.request_context.lifespan_context.app
    info = get_auth_client(ctx).userinfo()

    return WhoAmI(
        identity_id=info["sub"],
        identity_type="client" if isinstance(app, globus_sdk.ClientApp) else "user",
        username=info["preferred_username"],
        name=info["name"],
        identity_provider_display_name=info["identity_provider_display_name"],
        organization=info.get("organization"),
    )
