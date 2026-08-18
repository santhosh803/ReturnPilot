import logging
import os
import sqlite3

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

logger = logging.getLogger(__name__)


def _build_checkpointer():
    """
    Select the LangGraph checkpointer from LANGGRAPH_CHECKPOINT_BACKEND.

    - ``memory`` (default): in-process MemorySaver. Thread state is lost on restart.
    - ``sqlite``: durable across restarts via a local SQLite file
      (LANGGRAPH_SQLITE_PATH, default ``agent_checkpoints.sqlite``). Good for a single
      long-lived process; note a container with an ephemeral disk still loses the file
      when the container is replaced.
    - ``postgres``: durable and multi-process, using LANGGRAPH_POSTGRES_URL or
      DATABASE_URL. This is the recommended backend for Railway (ephemeral disk,
      multiple processes). Verified against live Postgres.

    Any import or connection failure degrades gracefully to MemorySaver so the agent
    keeps working rather than failing to boot.
    """
    backend = os.getenv("LANGGRAPH_CHECKPOINT_BACKEND", "memory").strip().lower()

    if backend in ("", "memory"):
        return MemorySaver()

    if backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            path = os.getenv("LANGGRAPH_SQLITE_PATH", "agent_checkpoints.sqlite")
            # check_same_thread=False: the WSGI server may serve requests across threads.
            conn = sqlite3.connect(path, check_same_thread=False)
            saver = SqliteSaver(conn)
            saver.setup()
            logger.info("LangGraph checkpointer: sqlite (%s)", path)
            return saver
        except Exception as e:
            logger.warning(
                "sqlite checkpointer unavailable (%s); falling back to MemorySaver", e
            )
            return MemorySaver()

    if backend == "postgres":
        try:
            from psycopg import Connection
            from psycopg.rows import dict_row
            from langgraph.checkpoint.postgres import PostgresSaver

            conn_string = os.getenv("LANGGRAPH_POSTGRES_URL") or os.getenv("DATABASE_URL")
            if not conn_string:
                raise RuntimeError(
                    "postgres checkpointer requires LANGGRAPH_POSTGRES_URL or DATABASE_URL"
                )
            # Open a long-lived connection directly (the same configuration
            # PostgresSaver.from_conn_string uses internally). We deliberately do NOT
            # use from_conn_string here: it is a context manager, and holding only its
            # yielded saver lets the manager be garbage-collected, which closes the
            # connection out from under us. A directly-owned connection lives for the
            # process lifetime.
            conn = Connection.connect(
                conn_string,
                autocommit=True,
                prepare_threshold=0,
                row_factory=dict_row,
            )
            saver = PostgresSaver(conn)
            saver.setup()
            logger.info("LangGraph checkpointer: postgres")
            return saver
        except Exception as e:
            logger.warning(
                "postgres checkpointer unavailable (%s); falling back to MemorySaver. "
                "Install with: uv add langgraph-checkpoint-postgres psycopg[binary]",
                e,
            )
            return MemorySaver()

    logger.warning(
        "Unknown LANGGRAPH_CHECKPOINT_BACKEND=%r; using MemorySaver", backend
    )
    return MemorySaver()


# Checkpointer for thread persistence (see _build_checkpointer for options).
memory_checkpointer = _build_checkpointer()

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
