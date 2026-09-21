from mcp.server.mcpserver import MCPServer

from globus_mcp.services.transfer.tools import ALL_TRANSFER_TOOLS


def register_transfer(mcp: MCPServer) -> None:
    for tool in ALL_TRANSFER_TOOLS:
        mcp.add_tool(tool)
