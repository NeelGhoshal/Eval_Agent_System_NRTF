"""Shared graph state and the data contracts each agent produces.

Each agent owns exactly one output key on `EvalState` and one result type below.
Changing an agent's output shape = edit its type here + its own agent.py.
Agents run in parallel, so they must never write to each other's keys.
"""
from typing import Literal, Optional, TypedDict

Severity = Literal["low", "medium", "high", "critical"]


# ---- Evaluation Agent -------------------------------------------------------
class EvaluationResult(TypedDict):
    overall_score: float  # 0.0 - 1.0
    criteria_scores: dict[str, float]  # e.g. clarity, rigor, completeness
    summary: str


# ---- Claim Verification Agent -----------------------------------------------
class ClaimCheck(TypedDict):
    claim: str
    verdict: Literal["supported", "unsupported", "contradicted", "unverifiable"]
    sources: list[str]  # URLs / citations backing the verdict
    notes: str


class ClaimVerificationResult(TypedDict):
    checks: list[ClaimCheck]


# ---- Authority Check Agent --------------------------------------------------
class AuthorityCheck(TypedDict):
    person: str
    claim: str
    has_authority: Optional[bool]  # None = could not determine
    basis: str  # credentials, role, jurisdiction, etc.


class AuthorityCheckResult(TypedDict):
    checks: list[AuthorityCheck]


# ---- Contradiction Agent ----------------------------------------------------
class Contradiction(TypedDict):
    statement_a: str
    statement_b: str
    scope: Literal["internal", "external"]  # within document vs. against other sources
    severity: Severity
    explanation: str


class ContradictionResult(TypedDict):
    contradictions: list[Contradiction]


# ---- Graph state ------------------------------------------------------------
class EvalState(TypedDict, total=False):
    # input
    document: str
    # one key per agent (no key shared => safe parallel fan-out)
    evaluation: EvaluationResult
    claim_verification: ClaimVerificationResult
    authority_check: AuthorityCheckResult
    contradictions: ContradictionResult
    # output
    report: dict
