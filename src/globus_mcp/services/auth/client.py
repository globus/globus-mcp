from globus_sdk import AuthClient
from mcp.server.mcpserver import Context

from globus_mcp.context import GlobusContext


def get_auth_client(ctx: Context[GlobusContext]) -> AuthClient:
    globus_ctx = ctx.request_context.lifespan_context
    if globus_ctx.auth_client is None:
        globus_ctx.auth_client = AuthClient(app=globus_ctx.app)
    return globus_ctx.auth_client
