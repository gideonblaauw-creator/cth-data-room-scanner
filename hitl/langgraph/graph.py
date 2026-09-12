"""
Compile the Scanner HITL review LangGraph.

Production-pattern: checkpointer + interrupt/resume (langgraph-production skill).
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from hitl.langgraph.config import configure_langsmith_project
from hitl.langgraph.nodes import (
    hitl_interrupt_gate,
    load_review_job,
    persist_locks,
    propose_suggestions,
)
from hitl.langgraph.state import ReviewGraphState


def build_review_graph() -> StateGraph:
    """Context → proposal → HITL interrupt → locks (Understanding Lab loop)."""
    builder = StateGraph(ReviewGraphState)
    builder.add_node("load_review_job", load_review_job)
    builder.add_node("propose_suggestions", propose_suggestions)
    builder.add_node("hitl_interrupt_gate", hitl_interrupt_gate)
    builder.add_node("persist_locks", persist_locks)

    builder.add_edge(START, "load_review_job")
    builder.add_edge("load_review_job", "propose_suggestions")
    builder.add_edge("propose_suggestions", "hitl_interrupt_gate")
    builder.add_edge("hitl_interrupt_gate", "persist_locks")
    builder.add_edge("persist_locks", END)
    return builder


def compile_review_graph(*, checkpointer: MemorySaver | None = None):
    configure_langsmith_project()
    cp = checkpointer or MemorySaver()
    return build_review_graph().compile(checkpointer=cp)
