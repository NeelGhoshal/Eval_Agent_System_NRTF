"""Evaluation Agent: evaluates the overall quality of a document.

Reads:  state["document"]
Writes: state["evaluation"]  (EvaluationResult)

This is the reference example of an agent calling the shared LLM (see llm.py).
"""
from ...llm import is_configured, snowflake_json
from ...state import EvalState, EvaluationResult
from .prompts import SYSTEM_PROMPT

CRITERIA = ["clarity", "rigor", "completeness", "structure"]


def evaluation_node(state: EvalState) -> dict:
    document = state["document"]

    if not is_configured():  # no Snowflake credentials yet: keep the skeleton runnable
        result: EvaluationResult = {
            "overall_score": 0.0,
            "criteria_scores": {c: 0.0 for c in CRITERIA},
            "summary": "[stub] Snowflake LLM not configured",
        }
        return {"evaluation": result}

    data = snowflake_json(
        f"Document:\n{document}\n\nReturn JSON: "
        '{"criteria_scores": {"clarity": 0-1, "rigor": 0-1, "completeness": 0-1, "structure": 0-1}, '
        '"summary": "short text"}',
        system=SYSTEM_PROMPT,
    )
    scores = {c: float(data["criteria_scores"].get(c, 0.0)) for c in CRITERIA}
    result = {
        "overall_score": sum(scores.values()) / len(scores),
        "criteria_scores": scores,
        "summary": data.get("summary", ""),
    }
    return {"evaluation": result}
