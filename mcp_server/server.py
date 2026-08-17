import os
import sys
import argparse
import django

# Setup Django ORM environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "returnpilot.settings")
if not django.apps.apps.ready:
    django.setup()

from mcp.server.mcpserver import MCPServer
from mcp_server import tools

# Initialize MCP server
mcp = MCPServer(
    name="ReturnPilot",
    instructions="ReturnPilot MCP Server — AI eCommerce Returns Management Platform tools",
)


@mcp.tool(
    name="lookup_order",
    description="Look up order details, items, delivery status, customer info, and return history by order ID or customer email.",
)
def lookup_order(order_id: str) -> dict:
    """Look up order details by order ID or customer email."""
    return tools.lookup_order(order_id)


@mcp.tool(
    name="check_return_eligibility",
    description="Check whether specific items from an order are eligible for return based on product category return policy.",
)
def check_return_eligibility(order_id: str, item_skus: list[str]) -> dict:
    """Check whether specific items from an order are eligible for return based on policy."""
    return tools.check_return_eligibility(order_id, item_skus)


@mcp.tool(
    name="initiate_return",
    description="Create a new return request for specified items with customer reason text.",
)
def initiate_return(order_id: str, item_skus: list[str], reason: str) -> dict:
    """Create a new return request for specified items with a free-text reason."""
    return tools.initiate_return(order_id, item_skus, reason)


@mcp.tool(
    name="classify_return_reason",
    description="Get or trigger AI classification of a customer return reason into standard return categories.",
)
def classify_return_reason(return_id: str) -> dict:
    """Get or trigger AI classification of the return reason."""
    return tools.classify_return_reason(return_id)


@mcp.tool(
    name="recommend_exchange",
    description="AI-powered exchange recommendation suggesting alternatives from the catalog based on return reason.",
)
def recommend_exchange(return_id: str) -> dict:
    """AI-powered exchange recommendation based on return reason and product catalog."""
    return tools.recommend_exchange(return_id)


@mcp.tool(
    name="flag_serial_returner",
    description="Check customer return history and metrics for serial return or abuse patterns.",
)
def flag_serial_returner(customer_email: str) -> dict:
    """Check customer return history for serial return or abuse patterns."""
    return tools.flag_serial_returner(customer_email)


@mcp.tool(
    name="process_refund",
    description="Process refund for a return request. Automatically pauses and triggers HITL gate for high-value or high-risk returns.",
)
def process_refund(
    return_id: str,
    decision: str,
    method: str = "original_payment",
    reason: str = "",
) -> dict:
    """Process refund for an approved return. Triggers HITL gate if high-value or high-risk."""
    return tools.process_refund(return_id, decision, method, reason)


@mcp.tool(
    name="list_pending_returns",
    description="List return requests filtered by status (pending, awaiting_approval, approved, rejected, exchanged).",
)
def list_pending_returns(status_filter: str = "pending", limit: int = 10) -> dict:
    """List return requests by status. Useful for merchant queue review."""
    return tools.list_pending_returns(status_filter, limit)


def main():
    parser = argparse.ArgumentParser(description="ReturnPilot MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode to run MCP server (stdio or sse)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE server",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        import uvicorn
        print(f"Starting ReturnPilot MCP Server in SSE mode on http://{args.host}:{args.port}/sse ...")
        starlette_app = mcp.sse_app()
        uvicorn.run(starlette_app, host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
