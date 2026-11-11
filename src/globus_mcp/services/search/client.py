import globus_sdk
from mcp.server.mcpserver import Context

from globus_mcp.context import GlobusContext


def get_search_client(ctx: Context[GlobusContext]) -> globus_sdk.SearchClient:
    globus_ctx = ctx.request_context.lifespan_context
    if globus_ctx.search_client:
        return globus_ctx.search_client

    client = globus_sdk.SearchClient(app=globus_ctx.app)
    globus_ctx.search_client = client
    return client
