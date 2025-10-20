import argparse

from mcp.server.fastmcp import FastMCP

from globus_mcp.context import lifespan
from globus_mcp.services.compute.registry import register_compute
from globus_mcp.services.transfer.registry import register_transfer

mcp = FastMCP("Globus MCP Server", lifespan=lifespan)


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
