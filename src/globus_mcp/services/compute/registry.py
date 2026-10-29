from mcp.server.mcpserver import MCPServer

from globus_mcp.services.compute.tools import ALL_COMPUTE_TOOLS


def register_compute(mcp: MCPServer) -> None:
    for tool in ALL_COMPUTE_TOOLS:
        mcp.add_tool(tool)
