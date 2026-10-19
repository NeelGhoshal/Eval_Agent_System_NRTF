"""Check Legitimate Authority Agent: checks whether the people involved in the document
have the rights/authority to make the claims they bring forth.

Reads:  state["document"]
Writes: state["authority_check"]  (AuthorityCheckResult)

Pipeline: extract (person, role, claim) (LLM) -> web search on the person -> LLM judges standing.
"""
from concurrent.futures import ThreadPoolExecutor

from ...llm import clip, snowflake_json
from ...state import AuthorityCheck, AuthorityCheckResult, EvalState
from ...tools import format_hits, web_search
from .prompts import (
    AUTHORITY_PROMPT,
    AUTHORITY_SYSTEM,
    EXTRACT_PEOPLE_PROMPT,
)

MAX_ACTORS = 5


def extract_actors(document: str) -> list[dict]:
    data = snowflake_json(EXTRACT_PEOPLE_PROMPT.format(document=clip(document), max_actors=MAX_ACTORS))
    actors = data.get("actors", []) if isinstance(data, dict) else data
    return [a for a in actors if isinstance(a, dict) and a.get("person")][:MAX_ACTORS]


def check_authority(actor: dict) -> AuthorityCheck:
    person, role, claim = actor["person"], actor.get("role", ""), actor.get("claim", "")
    hits = web_search(f"{person} {role}".strip())
    data = snowflake_json(
        AUTHORITY_PROMPT.format(person=person, role=role or "not stated", claim=claim, results=format_hits(hits)),
        system=AUTHORITY_SYSTEM,
    )
    verdict = data.get("has_authority")
    return {
        "person": str(person),
        "claim": str(claim),
        "has_authority": verdict if isinstance(verdict, bool) else None,
        "basis": str(data.get("basis", "")),
    }


def authority_check_node(state: EvalState) -> dict:
    actors = extract_actors(state["document"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(check_authority, actors))
    result: AuthorityCheckResult = {"checks": checks}
    return {"authority_check": result}
