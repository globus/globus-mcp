from mcp.server.fastmcp import FastMCP

from globus_mcp.services.transfer.tools import ALL_TRANSFER_TOOLS


def register_transfer(mcp: FastMCP) -> None:
    for tool in ALL_TRANSFER_TOOLS:
        mcp.add_tool(tool)
