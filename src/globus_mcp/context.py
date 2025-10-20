from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from globus_compute_sdk import Client
from globus_sdk import GlobusApp, TransferClient
from mcp.server.fastmcp import FastMCP

from globus_mcp.auth import get_globus_app


@dataclass
class GlobusContext:
    app: GlobusApp
    transfer_client: TransferClient | None = None
    compute_client: Client | None = None


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[GlobusContext]:
    try:
        app = get_globus_app()
        yield GlobusContext(app=app)
    finally:
        pass
