"""Identify Contradiction Agent: finds contradictions within and surrounding the document
and reports each with a severity level.

Reads:  state["document"]
Writes: state["contradictions"]  (ContradictionResult)
"""
from ...state import Contradiction, ContradictionResult, EvalState
from .prompts import EXTERNAL_PROMPT, INTERNAL_PROMPT  # noqa: F401


def find_internal(document: str) -> list[Contradiction]:
    # TODO: pairwise/LLM consistency check inside the document (INTERNAL_PROMPT)
    return []


def find_external(document: str) -> list[Contradiction]:
    # TODO: retrieve related sources and compare (EXTERNAL_PROMPT)
    return []


def contradiction_node(state: EvalState) -> dict:
    doc = state["document"]
    result: ContradictionResult = {"contradictions": find_internal(doc) + find_external(doc)}
    return {"contradictions": result}
