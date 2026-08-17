from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from .nodes import (
    AgentState,
    reason_node,
    act_node,
    hitl_check_node,
    route_after_reason,
    route_after_act,
)

# In-memory checkpointer for thread persistence
memory_checkpointer = MemorySaver()

# Build the LangGraph StateGraph
builder = StateGraph(AgentState)

builder.add_node("reason", reason_node)
builder.add_node("act", act_node)
builder.add_node("hitl", hitl_check_node)

builder.add_edge(START, "reason")
builder.add_conditional_edges(
    "reason",
    route_after_reason,
    {
        "act": "act",
        "end": END,
    },
)
builder.add_conditional_edges(
    "act",
    route_after_act,
    {
        "hitl": "hitl",
        "reason": "reason",
    },
)
builder.add_edge("hitl", END)

# Compiled agent graph with checkpointer
agent_app = builder.compile(checkpointer=memory_checkpointer)
