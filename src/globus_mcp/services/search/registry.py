from mcp.server.mcpserver import MCPServer

from globus_mcp.services.search.tools import ALL_SEARCH_TOOLS


def register_search(mcp: MCPServer) -> None:
    for tool in ALL_SEARCH_TOOLS:
        mcp.add_tool(tool)
