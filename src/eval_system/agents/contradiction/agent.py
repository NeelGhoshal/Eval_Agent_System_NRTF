"""Identify Contradiction Agent: finds contradictions within and surrounding the document
and reports each with a severity level.

Reads:  state["document"]
Writes: state["contradictions"]  (ContradictionResult)

Internal: one LLM pass over the document.
External: pick key statements -> web search -> LLM compares each against the results.
"""
from concurrent.futures import ThreadPoolExecutor

from ...llm import clip, snowflake_json
from ...state import Contradiction, ContradictionResult, EvalState
from ...tools import format_hits, web_search
from .prompts import (
    EXTERNAL_PROMPT,
    INTERNAL_PROMPT,
    KEY_STATEMENTS_PROMPT,
    SEVERITY_GUIDE,
)

SEVERITIES = ("low", "medium", "high", "critical")
MAX_EXTERNAL = 4


def _severity(value) -> str:
    return value if value in SEVERITIES else "medium"


def find_internal(document: str) -> list[Contradiction]:
    data = snowflake_json(INTERNAL_PROMPT.format(document=clip(document), severity_guide=SEVERITY_GUIDE))
    items = data.get("contradictions", []) if isinstance(data, dict) else data
    return [
        {
            "statement_a": str(c.get("statement_a", "")),
            "statement_b": str(c.get("statement_b", "")),
            "scope": "internal",
            "severity": _severity(c.get("severity")),
            "explanation": str(c.get("explanation", "")),
        }
        for c in items
        if isinstance(c, dict)
    ]


def _check_external(statement: str) -> list[Contradiction]:
    hits = web_search(statement)
    if not hits:
        return []
    data = snowflake_json(
        EXTERNAL_PROMPT.format(statement=statement, results=format_hits(hits), severity_guide=SEVERITY_GUIDE)
    )
    if data.get("contradicts") is not True:
        return []
    idx = data.get("source_index")
    source = f" (source: {hits[idx]['url']})" if isinstance(idx, int) and 0 <= idx < len(hits) else ""
    return [
        {
            "statement_a": statement,
            "statement_b": str(data.get("statement_b", "")),
            "scope": "external",
            "severity": _severity(data.get("severity")),
            "explanation": str(data.get("explanation", "")) + source,
        }
    ]


def find_external(document: str) -> list[Contradiction]:
    data = snowflake_json(KEY_STATEMENTS_PROMPT.format(document=clip(document), n=MAX_EXTERNAL))
    statements = data.get("statements", []) if isinstance(data, dict) else data
    statements = [str(s) for s in statements if str(s).strip()][:MAX_EXTERNAL]
    with ThreadPoolExecutor(max_workers=4) as pool:
        return [c for found in pool.map(_check_external, statements) for c in found]


def contradiction_node(state: EvalState) -> dict:
    doc = state["document"]
    result: ContradictionResult = {"contradictions": find_internal(doc) + find_external(doc)}
    return {"contradictions": result}
