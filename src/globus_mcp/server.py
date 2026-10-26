import argparse
from importlib.metadata import version as _get_distribution_version

from mcp.server.mcpserver import MCPServer

from globus_mcp.context import lifespan
from globus_mcp.services.compute.registry import register_compute
from globus_mcp.services.transfer.registry import register_transfer

SERVER_INSTRUCTIONS = """\
Use the Globus data platform to move, discover, and analyze scientific datasets.

NOTE: this MCP server only exposes the tools specified in server configuration. If you need a \
feature that is not provided, ask the user to enable it. \
NOTE: In the past, Globus Transfer collections were sometimes referred to as "endpoints", and old \
references/ api fields may use the terms interchangeably"""

mcp = MCPServer(
    "Globus Research Data Platform",
    lifespan=lifespan,
    version=_get_distribution_version("globus-mcp"),
    instructions=SERVER_INSTRUCTIONS,
    description="Globus: Automation for the research lifecycle",
)


service_registry = {
    "compute": register_compute,
    "transfer": register_transfer,
}
services = list(service_registry.keys())


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Globus MCP Server")
    parser.add_argument(
        "--services",
        nargs="+",
        choices=services,
        default=services,
        help="Globus services to install tools for. Defaults to all services.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    for service in args.services:
        service_registry[service](mcp)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
