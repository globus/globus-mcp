from globus_sdk import TransferClient
from mcp.server.mcpserver import Context

from globus_mcp.context import GlobusContext


def get_transfer_client(ctx: Context[GlobusContext]) -> TransferClient:
    globus_ctx = ctx.request_context.lifespan_context
    if globus_ctx.transfer_client:
        return globus_ctx.transfer_client

    client = TransferClient(app=globus_ctx.app)
    globus_ctx.transfer_client = client
    return client
