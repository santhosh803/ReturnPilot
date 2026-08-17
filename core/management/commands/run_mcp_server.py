from django.core.management.base import BaseCommand
from mcp_server.server import mcp
import uvicorn


class Command(BaseCommand):
    help = "Run the ReturnPilot MCP Server in stdio or SSE transport mode"

    def add_arguments(self, parser):
        parser.add_argument(
            "--transport",
            type=str,
            default="stdio",
            choices=["stdio", "sse"],
            help="Transport mode (stdio or sse)",
        )
        parser.add_argument(
            "--host",
            type=str,
            default="127.0.0.1",
            help="Host for SSE mode (default: 127.0.0.1)",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port for SSE mode (default: 8001)",
        )

    def handle(self, *args, **options):
        transport = options["transport"]
        host = options["host"]
        port = options["port"]

        if transport == "sse":
            self.stdout.write(
                self.style.SUCCESS(
                    f"Starting ReturnPilot MCP Server in SSE mode on http://{host}:{port}/sse"
                )
            )
            starlette_app = mcp.sse_app(host=host)
            uvicorn.run(starlette_app, host=host, port=port)
        else:
            mcp.run(transport="stdio")
