"""Rule-based doc_type detection and completeness checks (no LLM, deterministic).

Each rubric is a list of `Check`s; a check passes if its pattern matches anywhere in the
document. completeness = passed_required_checks / total_required_checks.
"""
import re
from typing import Literal, NamedTuple, Optional

from ...state import EvalFinding, Severity

DocType = Literal["nc_bill", "generic"]

I = re.IGNORECASE


def _re(pattern: str, flags: int = I) -> re.Pattern:
    return re.compile(pattern, flags)


# ---- doc_type detection -----------------------------------------------------
NC_BILL_MARKERS = [
    _re(r"GENERAL ASSEMBLY OF NORTH CAROLINA"),
    _re(r"SESSION \d{4}"),
    _re(r"A BILL TO BE ENTITLED"),
    _re(r"(HOUSE|SENATE) (JOINT )?(BILL|RESOLUTION) \d+"),  # resolutions are filed like bills
    _re(r"AN ACT TO"),
]


def detect_doc_type(document: str) -> DocType:
    hits = sum(bool(p.search(document)) for p in NC_BILL_MARKERS)
    return "nc_bill" if hits >= 2 else "generic"


# ---- rubrics ----------------------------------------------------------------
class Check(NamedTuple):
    code: str
    severity: Severity  # severity if missing
    message: str  # shown when missing
    pattern: re.Pattern
    required_if: Optional[re.Pattern] = None  # None = always required
    skip_if: Optional[re.Pattern] = None  # not required when this matches


NC_BILL_CHECKS = [
    Check(
        "MISSING_BILL_ID", "high", "No bill number with chamber (e.g. HOUSE BILL 123).",
        _re(r"\b(?:HOUSE|SENATE)\s+(?:JOINT\s+)?(?:BILL|RESOLUTION)\s+\d+\b|\b[HS]\.?\s?[BJR]\.?\s?\d+\b"),
    ),
    Check(
        "MISSING_TITLE", "critical", 'No title or "AN ACT TO..." clause.',
        _re(r"\bAN ACT\s+TO\b|\bShort Title\s*:|\bA\s+(?:(?:HOUSE|SENATE)\s+|JOINT\s+)?RESOLUTION\b"),
    ),
    Check(
        "MISSING_SPONSOR", "high", "No sponsor named.",
        # case-sensitive name part so "representative of" doesn't count
        _re(
            r"(?i:\bsponsors?\s*:|\bintroduced by\b)"
            r"|\b(?:Representatives?|Senators?|Reps?\.|Sens?\.)\s+[A-Z][a-z]+",
            0,
        ),
        # enacted/ratified text (session laws, ratified resolutions) doesn't print sponsors
        skip_if=_re(r"\bSESSION LAW\s+\d{4}-\d+|\bRATIFIED BILL\b|\bRESOLUTION\s+\d{4}-\d+"),
    ),
    Check("MISSING_SESSION", "medium", "No session year.", _re(r"\bSESSION\s+\d{4}\b|\b\d{4}\s+SESSION\b")),
    Check(
        "MISSING_EFFECTIVE_DATE", "medium", 'No effective date ("This act is effective...").',
        _re(r"\b(?:is|are|becomes?|shall become)\s+effective\b"),
    ),
    Check(
        "MISSING_FISCAL", "high", "Mentions money but gives no dollar amount, appropriation, or fiscal note.",
        # "appropriate" (adjective) deliberately doesn't satisfy the check, only real appropriations
        _re(r"\$\s?\d|\bappropriat(?:ed|es|ion|ions|ing)\b|\bfiscal note\b"),
        required_if=_re(r"\$|\bfunds?\b|\bfunding\b|\bfees?\b|\btax(?:es)?\b|\bappropriat\w*"),
    ),
    Check("NO_WAKE_REFERENCE", "low", 'Does not mention "Wake County".', _re(r"\bWake\s+County\b")),
]

_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

GENERIC_CHECKS = [
    Check(
        "NO_ACTOR", "high", "Does not name a person or body that acted.",
        _re(
            r"\b(?:Board|Council|Commission(?:ers)?|Committee|Department|Agency|General Assembly"
            r"|Legislature|Senate|House|Court|Governor|Mayor|County|City of|Town of)\b"
            r"|\b(?:Mr|Ms|Mrs|Dr|Sen|Rep|Gov)\.\s+[A-Z]"
            r"|\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:said|says|announced|voted|approved|signed|introduced|proposed)\b",
            0,
        ),
    ),
    Check(
        "NO_ACTION", "critical", "Does not state a concrete decision or action.",
        _re(
            r"\b(?:approved|voted|passed|adopted|enacted|signed|vetoed|awarded|allocated|appropriated"
            r"|authorized|rejected|denied|ordered|ruled|decided|requires?|directs?|prohibits?|amends?"
            r"|establish(?:es|ed)?|will\s+(?:require|provide|fund|create|allow|ban|prohibit|establish))\b"
        ),
    ),
    Check(
        "NO_DATE", "medium", "Does not include a date.",
        _re(
            rf"\b{_MONTH}\.?\s+(?:\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?|\d{{4}})\b"
            r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"
        ),
    ),
    Check(
        "NO_SOURCE", "medium", "Cites no source, link, or document reference.",
        _re(
            r"https?://|\bwww\.|\baccording to\b|\bsources?\s*:|\bcit(?:ed|ing)\b|\bpress release\b"
            r"|\breport(?:ed)? by\b|\b(?:HOUSE|SENATE)\s+BILL\s+\d+\b|\b[HS]\.?B\.?\s?\d+\b"
            r"|\bG\.S\.\s?\d|\bS\.L\.\s?\d{4}"
        ),
    ),
]

RUBRICS: dict[DocType, list[Check]] = {"nc_bill": NC_BILL_CHECKS, "generic": GENERIC_CHECKS}


# ---- scoring ----------------------------------------------------------------
class Completeness(NamedTuple):
    score: float  # 0.0 - 1.0
    passed: int
    total: int
    findings: list[EvalFinding]


def _snippet(document: str, m: re.Match, pad: int = 40) -> str:
    return " ".join(document[max(m.start() - pad, 0) : m.end() + pad].split())


def check_completeness(document: str, doc_type: DocType) -> Completeness:
    passed, total, findings = 0, 0, []
    for c in RUBRICS[doc_type]:
        trigger = c.required_if.search(document) if c.required_if else None
        if (c.required_if and not trigger) or (c.skip_if and c.skip_if.search(document)):
            continue  # not required for this document
        total += 1
        if c.pattern.search(document):
            passed += 1
        else:
            evidence = f"…{_snippet(document, trigger)}…" if trigger else None
            findings.append({"code": c.code, "severity": c.severity, "message": c.message, "evidence": evidence})
    return Completeness(passed / total if total else 0.0, passed, total, findings)
