from mcp.server.fastmcp import FastMCP

from globus_mcp.services.compute.tools import ALL_COMPUTE_TOOLS


def register_compute(mcp: FastMCP) -> None:
    for tool in ALL_COMPUTE_TOOLS:
        mcp.add_tool(tool)
