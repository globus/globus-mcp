from globus_compute_sdk import Client
from globus_compute_sdk.serialize import JSONData, PureSourceTextInspect
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from globus_mcp.context import GlobusContext


def get_compute_client(ctx: Context[ServerSession, GlobusContext]) -> Client:
    globus_ctx = ctx.request_context.lifespan_context
    if globus_ctx.compute_client:
        return globus_ctx.compute_client

    client = Client(
        app=globus_ctx.app,
        code_serialization_strategy=PureSourceTextInspect(),
        data_serialization_strategy=JSONData(),  # type: ignore[no-untyped-call]
        do_version_check=False,
    )
    globus_ctx.compute_client = client
    return client
