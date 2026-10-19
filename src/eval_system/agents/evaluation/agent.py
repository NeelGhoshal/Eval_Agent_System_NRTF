"""Evaluation Agent: evaluates the overall quality of a document.

Reads:  state["document"]
Writes: state["evaluation"]  (EvaluationResult)
"""
from ...llm import clip, snowflake_json
from ...state import EvalState, EvaluationResult
from .prompts import SYSTEM_PROMPT, USER_PROMPT

CRITERIA = ["clarity", "rigor", "completeness", "structure"]


def _score(value) -> float:
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def evaluation_node(state: EvalState) -> dict:
    data = snowflake_json(USER_PROMPT.format(document=clip(state["document"])), system=SYSTEM_PROMPT)
    scores = {c: _score(data.get("criteria_scores", {}).get(c)) for c in CRITERIA}
    result: EvaluationResult = {
        "overall_score": sum(scores.values()) / len(scores),
        "criteria_scores": scores,
        "summary": str(data.get("summary", "")),
    }
    return {"evaluation": result}
