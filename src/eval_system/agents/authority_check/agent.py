"""Check Legitimate Authority Agent: checks whether the people involved in the document
have the rights/authority to make the claims they bring forth.

Reads:  state["document"]
Writes: state["authority_check"]  (AuthorityCheckResult)
"""
from ...state import AuthorityCheck, AuthorityCheckResult, EvalState
from ...llm import snowflake_json, snowflake_llm  # noqa: F401  (shared Snowflake LLM)
from .prompts import AUTHORITY_PROMPT, EXTRACT_PEOPLE_PROMPT  # noqa: F401


def extract_actors(document: str) -> list[tuple[str, str]]:
    """Return (person, claim) pairs."""
    # TODO: LLM-based extraction (EXTRACT_PEOPLE_PROMPT)
    return []


def check_authority(person: str, claim: str) -> AuthorityCheck:
    # TODO: look up credentials/role via tools + LLM judgment (AUTHORITY_PROMPT)
    return {"person": person, "claim": claim, "has_authority": None, "basis": "[stub]"}


def authority_check_node(state: EvalState) -> dict:
    pairs = extract_actors(state["document"])
    result: AuthorityCheckResult = {"checks": [check_authority(p, c) for p, c in pairs]}
    return {"authority_check": result}
