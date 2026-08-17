import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "returnpilot.settings")
if not django.apps.apps.ready:
    django.setup()

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from mcp_server import tools as mcp_tools


@tool
def lookup_order(order_id: str) -> dict:
    """Look up order details, items, delivery status, customer info, and existing returns by order ID or customer email."""
    return mcp_tools.lookup_order(order_id)


@tool
def check_return_eligibility(order_id: str, item_skus: list[str]) -> dict:
    """Check whether specific items from an order are eligible for return based on category policy and delivery window."""
    return mcp_tools.check_return_eligibility(order_id, item_skus)


@tool
def initiate_return(order_id: str, item_skus: list[str], reason: str) -> dict:
    """Create a new return request for specified items with customer reason text."""
    return mcp_tools.initiate_return(order_id, item_skus, reason)


@tool
def classify_return_reason(return_id: str) -> dict:
    """Get or trigger AI classification of a customer return reason into standard return categories."""
    return mcp_tools.classify_return_reason(return_id)


@tool
def recommend_exchange(return_id: str) -> dict:
    """AI-powered exchange recommendation suggesting alternatives from the catalog based on return reason."""
    return mcp_tools.recommend_exchange(return_id)


@tool
def flag_serial_returner(customer_email: str) -> dict:
    """Check customer return history and metrics for serial return or abuse patterns."""
    return mcp_tools.flag_serial_returner(customer_email)


@tool
def process_refund(
    return_id: str,
    decision: str,
    method: str = "original_payment",
    reason: str = "",
) -> dict:
    """Process refund for a return request. Automatically pauses and triggers HITL gate for high-value (>$100) or high-risk (>0.75) returns."""
    return mcp_tools.process_refund(return_id, decision, method, reason)


@tool
def list_pending_returns(status_filter: str = "pending", limit: int = 10) -> dict:
    """List return requests filtered by status (pending, awaiting_approval, approved, rejected, exchanged)."""
    return mcp_tools.list_pending_returns(status_filter, limit)


def get_agent_tools() -> list:
    """Returns list of LangChain tools connected to ReturnPilot MCP tools."""
    return [
        lookup_order,
        check_return_eligibility,
        initiate_return,
        classify_return_reason,
        recommend_exchange,
        flag_serial_returner,
        process_refund,
        list_pending_returns,
    ]


def execute_mcp_tool(tool_name: str, args: dict) -> dict:
    """Execute MCP tool by name with arguments dict."""
    tool_map = {
        "lookup_order": mcp_tools.lookup_order,
        "check_return_eligibility": mcp_tools.check_return_eligibility,
        "initiate_return": mcp_tools.initiate_return,
        "classify_return_reason": mcp_tools.classify_return_reason,
        "recommend_exchange": mcp_tools.recommend_exchange,
        "flag_serial_returner": mcp_tools.flag_serial_returner,
        "process_refund": mcp_tools.process_refund,
        "list_pending_returns": mcp_tools.list_pending_returns,
    }
    func = tool_map.get(tool_name)
    if not func:
        return {"error": f"Tool '{tool_name}' not recognized"}
    return func(**args)
