"""Claim Verification Agent: verifies document claims against current citations and sources.

Reads:  state["document"]
Writes: state["claim_verification"]  (ClaimVerificationResult)

Pipeline: extract claims (LLM) -> web search per claim -> LLM judges the claim against the results.
Cited sources are always real URLs returned by the search, never LLM-invented.
"""
from concurrent.futures import ThreadPoolExecutor

from ...llm import clip, snowflake_json
from ...state import ClaimCheck, ClaimVerificationResult, EvalState
from ...tools import format_hits, web_search
from .prompts import (
    EXTRACT_CLAIMS_PROMPT,
    VERIFY_CLAIM_PROMPT,
    VERIFY_CLAIM_SYSTEM,
)

MAX_CLAIMS = 6
VERDICTS = {"supported", "unsupported", "contradicted", "unverifiable"}


def extract_claims(document: str) -> list[str]:
    data = snowflake_json(
        EXTRACT_CLAIMS_PROMPT.format(document=clip(document), max_claims=MAX_CLAIMS)
    )
    claims = data.get("claims", []) if isinstance(data, dict) else data
    return [str(c) for c in claims if str(c).strip()][:MAX_CLAIMS]


def verify_claim(claim: str) -> ClaimCheck:
    hits = web_search(claim)
    if not hits:
        return {"claim": claim, "verdict": "unverifiable", "sources": [], "notes": "No search results found."}
    data = snowflake_json(
        VERIFY_CLAIM_PROMPT.format(claim=claim, results=format_hits(hits)),
        system=VERIFY_CLAIM_SYSTEM,
    )
    verdict = data.get("verdict") if data.get("verdict") in VERDICTS else "unverifiable"
    sources = []
    for i in data.get("source_indices", []):
        if isinstance(i, int) and 0 <= i < len(hits) and hits[i]["url"] not in sources:
            sources.append(hits[i]["url"])
    return {"claim": claim, "verdict": verdict, "sources": sources, "notes": str(data.get("notes", ""))}


def claim_verification_node(state: EvalState) -> dict:
    claims = extract_claims(state["document"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(verify_claim, claims))
    result: ClaimVerificationResult = {"checks": checks}
    return {"claim_verification": result}
