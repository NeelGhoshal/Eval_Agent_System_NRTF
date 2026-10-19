"""Evaluation Agent: evaluates the overall quality of a document.

Reads:  state["document"]
Writes: state["evaluation"]  (EvaluationResult)
"""
from ...state import EvalState, EvaluationResult
from .prompts import SYSTEM_PROMPT  # noqa: F401  (used once an LLM is wired in)

CRITERIA = ["clarity", "rigor", "completeness", "structure"]


def evaluation_node(state: EvalState) -> dict:
    document = state["document"]

    # TODO: replace this stub with real logic (LLM call using SYSTEM_PROMPT, rubric scoring, ...)
    result: EvaluationResult = {
        "overall_score": 0.0,
        "criteria_scores": {c: 0.0 for c in CRITERIA},
        "summary": f"[stub] evaluated {len(document)} characters",
    }
    return {"evaluation": result}
