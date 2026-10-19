"""Claim Verification Agent: verifies document claims against current citations and sources.

Reads:  state["document"]
Writes: state["claim_verification"]  (ClaimVerificationResult)
"""
from ...state import ClaimCheck, ClaimVerificationResult, EvalState
from ...llm import snowflake_json, snowflake_llm  # noqa: F401  (shared Snowflake LLM)
from .prompts import EXTRACT_CLAIMS_PROMPT, VERIFY_CLAIM_PROMPT  # noqa: F401


def extract_claims(document: str) -> list[str]:
    # TODO: LLM-based claim extraction (EXTRACT_CLAIMS_PROMPT)
    return []


def verify_claim(claim: str) -> ClaimCheck:
    # TODO: web search / citation lookup tool + LLM judgment (VERIFY_CLAIM_PROMPT)
    return {"claim": claim, "verdict": "unverifiable", "sources": [], "notes": "[stub]"}


def claim_verification_node(state: EvalState) -> dict:
    claims = extract_claims(state["document"])
    result: ClaimVerificationResult = {"checks": [verify_claim(c) for c in claims]}
    return {"claim_verification": result}
