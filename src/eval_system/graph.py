"""Wires the four agents into a LangGraph.

START -> (evaluation | claim_verification | authority_check | contradiction) -> aggregate -> END

The four agents run in parallel (fan-out) and join at `aggregate` (fan-in).
To add a dependency between agents (e.g. contradiction after claim_verification),
change the edges here only.
"""
import logging

from langgraph.graph import END, START, StateGraph

from .agents import (
    authority_check_node,
    claim_verification_node,
    contradiction_node,
    evaluation_node,
)
from .state import EvalState

AGENT_NODES = {
    "evaluation": evaluation_node,
    "claim_verification": claim_verification_node,
    "authority_check": authority_check_node,
    "contradiction": contradiction_node,
}


def isolated(name, fn):
    """One failing agent (bad LLM reply, network error...) must not take down the others."""

    def run(state: EvalState) -> dict:
        try:
            return fn(state)
        except Exception as e:  # noqa: BLE001
            logging.exception("agent %s failed", name)
            return {"errors": {name: f"{type(e).__name__}: {e}"}}

    return run


def aggregate_node(state: EvalState) -> dict:
    return {
        "report": {
            "evaluation": state.get("evaluation"),
            "claim_verification": state.get("claim_verification"),
            "authority_check": state.get("authority_check"),
            "contradictions": state.get("contradictions"),
            "errors": state.get("errors", {}),
        }
    }


def build_graph():
    g = StateGraph(EvalState)
    g.add_node("aggregate", aggregate_node)
    for name, fn in AGENT_NODES.items():
        g.add_node(name, isolated(name, fn))
        g.add_edge(START, name)
        g.add_edge(name, "aggregate")
    g.add_edge("aggregate", END)
    return g.compile()
