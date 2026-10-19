"""Evaluation Agent: scores the structural and procedural quality of a document.

Does NOT check truth (Claim Verification), authority (Authority Check), or consistency
(Contradiction). Three dimensions, each 0.0-1.0:
  completeness  0.50  rules (rules.py), per doc_type rubric
  provenance    0.25  LLM judge: does it cite traceable sources?
  clarity       0.25  LLM judge: is the action/purpose specific?

Reads:  state["document"]
Writes: state["evaluation"]  (EvaluationResult)
"""
import logging
from typing import Optional

from pydantic import BaseModel, Field

from ...llm import clip, is_configured, snowflake_json
from ...state import EvalFinding, EvalState, EvaluationResult
from .prompts import JUDGE_PROMPT, JUDGE_SYSTEM
from .rules import check_completeness, detect_doc_type

log = logging.getLogger(__name__)

WEIGHTS = {"completeness": 0.50, "provenance": 0.25, "clarity": 0.25}
LOW_SCORE = 2  # LLM scores <= this add a finding
LLM_ATTEMPTS = 2  # snowflake_llm has no retries of its own
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DOC_LABEL = {"nc_bill": "NC bill", "generic": "Generic document"}


class JudgeOutput(BaseModel):
    provenance: int = Field(ge=0, le=5)
    clarity: int = Field(ge=0, le=5)
    provenance_reason: str
    clarity_reason: str


def judge(document: str, doc_type: str) -> Optional[JudgeOutput]:
    """One LLM call scoring provenance + clarity. None if unavailable; never raises."""
    if not is_configured():
        return None
    prompt = JUDGE_PROMPT.format(doc_type=doc_type, document=clip(document))
    for attempt in range(1, LLM_ATTEMPTS + 1):
        try:
            return JudgeOutput.model_validate(snowflake_json(prompt, system=JUDGE_SYSTEM))
        except Exception as e:  # HTTP/timeout, no JSON, or wrong shape: retry, then give up
            first_line = str(e).splitlines()[0] if str(e) else type(e).__name__
            log.warning("evaluation judge attempt %d/%d failed: %s", attempt, LLM_ATTEMPTS, first_line)
    return None


def _finding(code: str, severity: str, message: str, evidence: Optional[str] = None) -> EvalFinding:
    return {"code": code, "severity": severity, "message": message, "evidence": evidence}


def evaluation_node(state: EvalState) -> dict:
    document = state["document"]
    doc_type = detect_doc_type(document)
    completeness = check_completeness(document, doc_type)
    findings = list(completeness.findings)

    verdict = judge(document, doc_type)
    if verdict:
        provenance, clarity = verdict.provenance / 5, verdict.clarity / 5
        overall = (
            WEIGHTS["completeness"] * completeness.score
            + WEIGHTS["provenance"] * provenance
            + WEIGHTS["clarity"] * clarity
        )
        if verdict.provenance <= LOW_SCORE:
            findings.append(_finding("LOW_PROVENANCE", "medium", "Few traceable sources or references.", verdict.provenance_reason))
        if verdict.clarity <= LOW_SCORE:
            findings.append(_finding("LOW_CLARITY", "medium", "Action or purpose is vague.", verdict.clarity_reason))
        llm_note = f"provenance {verdict.provenance}/5, clarity {verdict.clarity}/5"
    else:
        provenance = clarity = None
        overall = completeness.score
        reason = "LLM not configured" if not is_configured() else "LLM call failed"
        findings.append(_finding("LLM_UNAVAILABLE", "low", f"{reason}; score is from completeness rules only."))
        llm_note = "LLM judge unavailable"

    findings.sort(key=lambda f: SEVERITY_RANK[f["severity"]])
    issues = [f for f in findings if f["code"] != "LLM_UNAVAILABLE"]
    worst = f", worst {issues[0]['severity']}" if issues else ""
    summary = (
        f"{DOC_LABEL[doc_type]}: {completeness.passed}/{completeness.total} required parts present; "
        f"{llm_note}. {len(issues)} issue(s){worst}."
    )

    result: EvaluationResult = {
        "doc_type": doc_type,
        "overall_score": round(overall, 3),
        "criteria_scores": {
            "completeness": round(completeness.score, 3),
            "provenance": provenance,
            "clarity": clarity,
        },
        "findings": findings,
        "summary": summary,
    }
    return {"evaluation": result}
