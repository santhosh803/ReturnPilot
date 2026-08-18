import json
import logging
from typing import Annotated, Sequence, TypedDict, List, Dict, Any, Optional
from django.conf import settings
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.graph.message import add_messages
from .prompts import RETURNPILOT_SYSTEM_PROMPT
from .mcp_client import get_agent_tools, execute_mcp_tool

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    intermediate_steps: List[Dict[str, Any]]
    hitl_pending: bool
    hitl_details: Optional[Dict[str, Any]]
    session_id: str


def get_agent_llm():
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            vertexai=True,
            project=getattr(settings, "GOOGLE_CLOUD_PROJECT", "ai-projects-500402"),
            location=getattr(settings, "GOOGLE_CLOUD_LOCATION", "us-central1"),
            temperature=0.1,
        )
        tools = get_agent_tools()
        return llm.bind_tools(tools)
    except Exception as e:
        logger.warning(f"Could not bind Gemini chat model: {e}")
        return None


def reason_node(state: AgentState) -> dict:
    """
    Reason node: Calls Gemini with conversation messages + tools to determine next action or final response.
    """
    messages = list(state.get("messages", []))
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=RETURNPILOT_SYSTEM_PROMPT)] + messages

    llm_with_tools = get_agent_llm()
    if llm_with_tools:
        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Error calling LLM in reason_node: {e}")

    # Fallback heuristic reasoning if LLM is unavailable
    last_user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_user_msg = m.content
            break

    # Look for order id pattern
    import re
    order_match = re.search(r"ORD-[\w-]+", last_user_msg, re.IGNORECASE)
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", last_user_msg)

    # Check already executed tools
    steps = state.get("intermediate_steps", [])
    executed_tools = [s.get("tool") for s in steps]

    if order_match and "lookup_order" not in executed_tools:
        order_id = order_match.group(0).upper()
        ai_msg = AIMessage(
            content=f"Looking up details for order {order_id}...",
            tool_calls=[{
                "name": "lookup_order",
                "args": {"order_id": order_id},
                "id": f"call_lookup_{order_id}",
            }],
        )
        return {"messages": [ai_msg]}

    if "lookup_order" in executed_tools and "check_return_eligibility" not in executed_tools:
        # Get order items from previous step
        lookup_step = next(s for s in steps if s.get("tool") == "lookup_order")
        items = lookup_step.get("result", {}).get("items", [])
        order_id = lookup_step.get("result", {}).get("order", {}).get("order_id", "ORD-UNKNOWN")
        skus = [i.get("sku") for i in items] if items else []
        ai_msg = AIMessage(
            content="Checking return eligibility for order items...",
            tool_calls=[{
                "name": "check_return_eligibility",
                "args": {"order_id": order_id, "item_skus": skus},
                "id": f"call_elig_{order_id}",
            }],
        )
        return {"messages": [ai_msg]}

    if "check_return_eligibility" in executed_tools and "flag_serial_returner" not in executed_tools:
        lookup_step = next(s for s in steps if s.get("tool") == "lookup_order")
        customer_email = lookup_step.get("result", {}).get("customer", {}).get("email", "")
        ai_msg = AIMessage(
            content="Checking customer risk profile and return history...",
            tool_calls=[{
                "name": "flag_serial_returner",
                "args": {"customer_email": customer_email},
                "id": f"call_risk_{customer_email}",
            }],
        )
        return {"messages": [ai_msg]}

    if "flag_serial_returner" in executed_tools and "initiate_return" not in executed_tools:
        lookup_step = next(s for s in steps if s.get("tool") == "lookup_order")
        order_id = lookup_step.get("result", {}).get("order", {}).get("order_id", "")
        items = lookup_step.get("result", {}).get("items", [])
        skus = [i.get("sku") for i in items]
        ai_msg = AIMessage(
            content="Initiating return request...",
            tool_calls=[{
                "name": "initiate_return",
                "args": {"order_id": order_id, "item_skus": skus, "reason": last_user_msg},
                "id": f"call_init_{order_id}",
            }],
        )
        return {"messages": [ai_msg]}

    if "initiate_return" in executed_tools and "process_refund" not in executed_tools:
        init_step = next(s for s in steps if s.get("tool") == "initiate_return")
        return_id = init_step.get("result", {}).get("return_id", "")
        ai_msg = AIMessage(
            content="Evaluating refund and checking merchant thresholds...",
            tool_calls=[{
                "name": "process_refund",
                "args": {"return_id": return_id, "decision": "approved"},
                "id": f"call_refund_{return_id}",
            }],
        )
        return {"messages": [ai_msg]}

    # Default fallback completion response
    summary = "I have processed your request across all relevant return workflows."
    return {"messages": [AIMessage(content=summary)]}


def act_node(state: AgentState) -> dict:
    """
    Act node: Executes tool calls produced by the reason node via the MCP client.
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    if not last_msg or not getattr(last_msg, "tool_calls", None):
        return {}

    tool_messages = []
    steps = list(state.get("intermediate_steps", []))
    hitl_pending = False
    hitl_details = None

    for call in last_msg.tool_calls:
        tool_name = call.get("name")
        tool_args = call.get("args", {})
        tool_id = call.get("id", f"call_{tool_name}")

        try:
            result = execute_mcp_tool(tool_name, tool_args)
        except Exception as e:
            result = {"error": str(e)}

        steps.append({
            "tool": tool_name,
            "args": tool_args,
            "result": result,
        })

        tool_messages.append(
            ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=tool_id,
                name=tool_name,
            )
        )

        if isinstance(result, dict) and result.get("hitl_triggered"):
            hitl_pending = True
            hitl_details = result

    update = {
        "messages": tool_messages,
        "intermediate_steps": steps,
    }
    if hitl_pending:
        update["hitl_pending"] = True
        update["hitl_details"] = hitl_details

    return update


def hitl_check_node(state: AgentState) -> dict:
    """
    HITL node: Pauses agent execution and informs the merchant that review is required.
    """
    details = state.get("hitl_details") or {}
    reason = details.get("hitl_reason", "Merchant review required.")
    risk_sum = details.get("risk_summary", "")
    return_id = details.get("return_id", "pending return")
    refund_amount = details.get("refund_amount", 0.0)

    notice = (
        f"⚠️ **Human-In-The-Loop Review Required**\n\n"
        f"Return `{return_id}` for **${refund_amount:.2f}** requires merchant authorization.\n"
        f"• **Reason:** {reason}\n"
        f"• **Risk Summary:** {risk_sum}\n\n"
        f"Please click **Approve** or **Reject** to complete this return."
    )
    return {
        "messages": [AIMessage(content=notice)],
        "hitl_pending": True,
    }


def route_after_reason(state: AgentState) -> str:
    messages = state.get("messages", [])
    if messages and getattr(messages[-1], "tool_calls", None):
        return "act"
    return "end"


def route_after_act(state: AgentState) -> str:
    if state.get("hitl_pending"):
        return "hitl"
    return "reason"
