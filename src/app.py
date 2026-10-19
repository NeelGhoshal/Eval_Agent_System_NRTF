"""Streamlit UI. Local: cd src && streamlit run app.py"""
import html
import json
import os
import time
import tomllib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from eval_system import llm
from eval_system.graph import AGENT_NODES, build_graph
from eval_system.observability import init_sentry

# Credentials: env vars, else src/.streamlit/secrets.toml (found relative to this file, so it works
# from any working directory), else Streamlit Cloud's Secrets.
_KEYS = (
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_TOKEN", "SNOWFLAKE_MODEL", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY",
    "SNOWFLAKE_WAREHOUSE", "SENTRY_DSN", "SENTRY_ENVIRONMENT", "SENTRY_TRACES_SAMPLE_RATE",
)
_local = Path(__file__).parent / ".streamlit" / "secrets.toml"
if _local.exists():
    _vals = tomllib.loads(_local.read_text(encoding="utf-8"))
    for _key in _KEYS:
        if _key in _vals:
            os.environ.setdefault(_key, str(_vals[_key]))
for _key in _KEYS:
    try:
        if _key in st.secrets:
            os.environ.setdefault(_key, str(st.secrets[_key]))
    except Exception:  # no secrets configured
        pass

init_sentry()  # after secrets are loaded; no-op without SENTRY_DSN

APP_VERSION = "v0.1 · ATO Hackathon"
SEVERITY_ORDER = ["critical", "high", "medium", "low"]
SEVERITY_COLOR = {"critical": "#EF4444", "high": "#F97316", "medium": "#F59E0B", "low": "#64748B"}
VERDICT_COLOR = {"supported": "#22C55E", "contradicted": "#EF4444", "unsupported": "#F59E0B", "unverifiable": "#64748B"}
AUTHORITY_STATUS = {True: ("Authorized", "#22C55E"), False: ("Not authorized", "#EF4444"), None: ("Undetermined", "#64748B")}
STATUS_COLOR = {"Ready": "#22C55E", "Needs review": "#F59E0B", "High risk": "#EF4444", "Incomplete": "#64748B"}
AGENT_KEYS = ("evaluation", "claim_verification", "authority_check", "contradictions")
DOC_TYPE_LABEL = {"nc_bill": "NC bill", "generic": "Generic document"}
GOOD, OFF = "#22C55E", "#64748B"

# Demo documents (src/demo_data/samples), label -> file
SAMPLES_DIR = Path(__file__).parent / "demo_data" / "samples"
SAMPLES = {
    "NC Senate Bill 2 (complete)": "s2_complete.txt",
    "NC Senate Bill 2 (sponsor, fiscal, effective date removed)": "s2_flawed.txt",
    "News article (illustrative, no sources)": "news_article.txt",
}
PASTE_OWN = "Paste your own..."

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stTextArea textarea, button { font-family: 'Inter', system-ui, sans-serif; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1240px; }
[data-testid="stSidebar"] { border-right: 1px solid #1F2430; }
.vx-logo { font-weight: 700; font-size: 1.15rem; letter-spacing: -0.01em; }
.vx-logo span { color: #6366F1; margin-right: .4rem; }
.vx-tag { color: #8B93A7; font-size: .8rem; margin-top: -.2rem; }
.vx-section { color: #8B93A7; font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; margin: 1.2rem 0 .4rem; }
.vx-status { display: flex; justify-content: space-between; align-items: center; font-size: .82rem; padding: .35rem 0; border-bottom: 1px solid #1F2430; }
.vx-status small { color: #8B93A7; display: block; font-size: .72rem; }
.vx-foot { color: #8B93A7; font-size: .72rem; margin-top: 1.5rem; }
.vx-crumb { color: #8B93A7; font-size: .8rem; }
.vx-crumb b { color: #E6E8EE; font-weight: 500; }
.vx-h1 { font-size: 1.6rem; font-weight: 600; letter-spacing: -0.02em; margin: .2rem 0 0; }
.vx-sub { color: #8B93A7; font-size: .9rem; margin-bottom: 1rem; }
.vx-chip { display: inline-flex; align-items: center; gap: .35rem; padding: .1rem .55rem; border-radius: 999px;
           font-size: .72rem; font-weight: 600; border: 1px solid; white-space: nowrap; }
.vx-chip::before { content: ""; width: .4rem; height: .4rem; border-radius: 50%; background: currentColor; }
.vx-banner { border: 1px solid #1F2430; border-left-width: 4px; background: #12151C; border-radius: 10px;
             padding: .9rem 1.1rem; margin: .5rem 0 1rem; }
.vx-banner .vx-why { margin: .35rem 0 .3rem; font-size: .92rem; }
.vx-meta { color: #8B93A7; font-size: .76rem; }
.vx-meta code { color: #8B93A7; background: transparent; }
.vx-cards { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .75rem; margin-bottom: 1rem; }
.vx-card { background: #12151C; border: 1px solid #1F2430; border-radius: 10px; padding: .9rem 1rem; min-height: 116px; }
.vx-card .lbl { color: #8B93A7; font-size: .74rem; font-weight: 500; }
.vx-card .val { font-size: 1.7rem; font-weight: 600; letter-spacing: -0.02em; margin: .25rem 0 .35rem; }
.vx-card .val small { color: #8B93A7; font-size: .95rem; font-weight: 500; }
.vx-card .ft { color: #8B93A7; font-size: .74rem; display: flex; flex-wrap: wrap; gap: .3rem; }
.vx-bar { height: 4px; background: #1F2430; border-radius: 4px; overflow: hidden; margin-top: .25rem; }
.vx-bar div { height: 100%; background: #6366F1; }
.vx-crit { display: grid; grid-template-columns: 110px 1fr 46px; align-items: center; gap: .75rem; font-size: .84rem; margin: .35rem 0; }
.vx-table { width: 100%; border-collapse: collapse; font-size: .84rem; }
.vx-table th { text-align: left; color: #8B93A7; font-weight: 500; font-size: .72rem; text-transform: uppercase;
               letter-spacing: .06em; padding: .5rem .6rem; border-bottom: 1px solid #1F2430; }
.vx-table td { padding: .6rem; border-bottom: 1px solid #1F2430; vertical-align: top; }
.vx-table td.muted, .vx-muted { color: #8B93A7; }
.vx-table code { font-size: .76rem; }
.vx-table a { color: #A5B4FC; text-decoration: none; word-break: break-all; }
.vx-error { border: 1px solid #7F1D1D; background: rgba(239, 68, 68, .08); border-radius: 10px; padding: .8rem 1rem; font-size: .86rem; }
.vx-error b { color: #FCA5A5; }
.vx-empty { color: #8B93A7; font-size: .86rem; padding: 1rem 0; }
@media (max-width: 900px) { .vx-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
"""

st.set_page_config(page_title="Veritas — Document Review", page_icon="◆", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def get_graph():
    return build_graph()


def load_sample():
    choice = st.session_state["sample"]
    if choice != PASTE_OWN:
        st.session_state["document"] = (SAMPLES_DIR / SAMPLES[choice]).read_text(encoding="utf-8")


# ---- HTML helpers (every model/user string goes through esc) -----------------
def esc(value) -> str:
    return html.escape(str(value), quote=True)


def chip(label: str, color: str) -> str:
    return f'<span class="vx-chip" style="color:{color};border-color:{color}55;background:{color}14">{esc(label)}</span>'


def card(label: str, value: str, footer: str = "", bar: float | None = None) -> str:
    bar_html = f'<div class="vx-bar"><div style="width:{bar * 100:.0f}%"></div></div>' if bar is not None else ""
    return f'<div class="vx-card"><div class="lbl">{esc(label)}</div><div class="val">{value}</div>{bar_html}<div class="ft">{footer}</div></div>'


def link(url: str) -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(url)}</a>' if url.startswith(("http://", "https://")) else esc(url)


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(rows_cell for rows_cell in r) + "</tr>" for r in rows)
    return f'<table class="vx-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def html_block(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def agent_error(report, agent: str) -> None:
    msg = report.get("errors", {}).get(agent, "No result returned.")
    html_block(f'<div class="vx-error"><b>Agent unavailable.</b> {esc(msg)}</div>')


def worst_severity(items) -> str | None:
    present = {i["severity"] for i in items}
    return next((s for s in SEVERITY_ORDER if s in present), None)


# ---- sidebar ------------------------------------------------------------------
def render_sidebar() -> None:
    model = os.environ.get("SNOWFLAKE_MODEL") or llm.DEFAULT_MODEL
    llm_ok = llm.is_configured()
    sentry_on = bool(os.environ.get("SENTRY_DSN"))
    with st.sidebar:
        html_block('<div class="vx-logo"><span>◆</span>Veritas</div><div class="vx-tag">Document integrity review</div>')
        html_block('<div class="vx-section">New review</div>')
        st.selectbox("Load sample", [PASTE_OWN, *SAMPLES], key="sample", on_change=load_sample)
        html_block('<div class="vx-section">System status</div>')
        rows = [
            ("LLM", f"Snowflake Cortex · {model}", chip("Connected", GOOD) if llm_ok else chip("Not configured", SEVERITY_COLOR["high"])),
            ("Error monitoring", "Sentry", chip("On", GOOD) if sentry_on else chip("Off", OFF)),
            ("Agents", "Evaluation, claims, authority, contradictions", chip(f"{len(AGENT_NODES)} online", GOOD)),
        ]
        html_block("".join(
            f'<div class="vx-status"><div>{esc(name)}<small>{esc(detail)}</small></div>{status}</div>'
            for name, detail, status in rows
        ))
        html_block(f'<div class="vx-foot">{esc(APP_VERSION)}</div>')


# ---- verdict + KPIs -------------------------------------------------------------
def verdict(report) -> tuple[str, str]:
    """Overall status + one-line rationale from all agents' results."""
    e, cv, co = report["evaluation"], report["claim_verification"], report["contradictions"]
    score = e["overall_score"] if e else None
    severities = {f["severity"] for f in e["findings"]} if e else set()
    contradicted = sum(c["verdict"] == "contradicted" for c in cv["checks"]) if cv else 0
    serious_contra = [c for c in co["contradictions"] if c["severity"] in ("high", "critical")] if co else []

    reasons = []
    if "critical" in severities:
        reasons.append("critical structural findings")
    if score is not None and score < 0.6:
        reasons.append(f"low integrity score ({score:.2f})")
    if contradicted:
        reasons.append(f"{contradicted} claim(s) contradicted by sources")
    if serious_contra:
        reasons.append(f"{len(serious_contra)} high-severity contradiction(s)")
    if reasons:
        return "High risk", "; ".join(reasons).capitalize() + "."
    missing = sum(report[k] is None for k in AGENT_KEYS)
    if missing:  # never call a partial run "Ready"
        return "Incomplete", f"{missing} of {len(AGENT_KEYS)} agents unavailable; results are partial."
    if score is not None and score >= 0.85 and not severities & {"high", "critical"}:
        return "Ready", f"Integrity score {score:.2f} with no high-severity findings or contradicted claims."
    detail = f"Integrity score {score:.2f}" if score is not None else "Evaluation unavailable"
    if severities & {"high"}:
        detail += "; high-severity findings need attention"
    return "Needs review", detail + "."


def render_banner(report, meta) -> None:
    status, why = verdict(report)
    color = STATUS_COLOR[status]
    html_block(
        f'<div class="vx-banner" style="border-left-color:{color}">{chip(status, color)}'
        f'<div class="vx-why">{esc(why)}</div>'
        f'<div class="vx-meta">Run <code>{esc(meta["run_id"])}</code> · {meta["elapsed"]:.1f}s · '
        f'{esc(meta["at"])} · {esc(meta["model"])} · {len(AGENT_NODES)} agents</div></div>'
    )


def render_kpis(report) -> None:
    e, cv, au, co = (report[k] for k in AGENT_KEYS)
    na = '<span class="vx-muted">agent unavailable</span>'
    cards = []
    if e:
        s = e["overall_score"]
        cards.append(card("Integrity score", f"{s:.2f}", esc(DOC_TYPE_LABEL.get(e["doc_type"], e["doc_type"])), bar=min(max(s, 0), 1)))
        counts = {sev: sum(f["severity"] == sev for f in e["findings"]) for sev in SEVERITY_ORDER}
        chips = "".join(chip(f"{n} {sev}", SEVERITY_COLOR[sev]) for sev, n in counts.items() if n) or "No findings"
        cards.append(card("Findings", str(len(e["findings"])), chips))
    else:
        cards += [card("Integrity score", "—", na), card("Findings", "—", na)]
    if cv:
        sup = sum(c["verdict"] == "supported" for c in cv["checks"])
        bad = sum(c["verdict"] == "contradicted" for c in cv["checks"])
        foot = chip(f"{bad} contradicted", VERDICT_COLOR["contradicted"]) if bad else "Verified against sources"
        cards.append(card("Claims supported", f"{sup}<small> / {len(cv['checks'])}</small>", foot))
    else:
        cards.append(card("Claims supported", "—", na))
    if au:
        ok = sum(c["has_authority"] is True for c in au["checks"])
        cards.append(card("Authority", f"{ok}<small> / {len(au['checks'])}</small>", "Actors with standing"))
    else:
        cards.append(card("Authority", "—", na))
    if co:
        worst = worst_severity(co["contradictions"])
        foot = chip(f"worst: {worst}", SEVERITY_COLOR[worst]) if worst else "None found"
        cards.append(card("Contradictions", str(len(co["contradictions"])), foot))
    else:
        cards.append(card("Contradictions", "—", na))
    html_block(f'<div class="vx-cards">{"".join(cards)}</div>')


# ---- tabs ---------------------------------------------------------------------
def show_overview(e) -> None:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("##### Quality criteria")
        rows = []
        for name, score in e["criteria_scores"].items():
            width = 0 if score is None else score * 100
            value = "n/a" if score is None else f"{score:.2f}"
            rows.append(f'<div class="vx-crit"><span>{esc(name.capitalize())}</span>'
                        f'<div class="vx-bar"><div style="width:{width:.0f}%"></div></div><span class="vx-muted">{value}</span></div>')
        html_block("".join(rows))
    with right:
        st.markdown("##### Summary")
        html_block(f'<div class="vx-muted" style="font-size:.88rem">{esc(e["summary"])}</div>')
    st.markdown("##### Findings")
    findings = sorted(e["findings"], key=lambda f: SEVERITY_ORDER.index(f["severity"]))
    if not findings:
        html_block('<div class="vx-empty">No findings. All structural checks passed.</div>')
        return
    html_block(table(
        ["Severity", "Code", "Finding", "Evidence"],
        [[f"<td>{chip(f['severity'], SEVERITY_COLOR[f['severity']])}</td>", f"<td><code>{esc(f['code'])}</code></td>",
          f"<td>{esc(f['message'])}</td>", f'<td class="muted">{esc(f.get("evidence") or "—")}</td>'] for f in findings],
    ))


def show_claims(r) -> None:
    if not r["checks"]:
        html_block('<div class="vx-empty">No verifiable claims extracted.</div>')
        return
    html_block(table(
        ["Verdict", "Claim", "Notes", "Sources"],
        [[f"<td>{chip(c['verdict'], VERDICT_COLOR.get(c['verdict'], OFF))}</td>", f"<td>{esc(c['claim'])}</td>",
          f'<td class="muted">{esc(c["notes"] or "—")}</td>',
          "<td>" + ("<br>".join(link(s) for s in c["sources"]) or '<span class="vx-muted">—</span>') + "</td>"]
         for c in r["checks"]],
    ))


def show_authority(r) -> None:
    if not r["checks"]:
        html_block('<div class="vx-empty">No actors identified.</div>')
        return
    rows = []
    for c in r["checks"]:
        label, color = AUTHORITY_STATUS[c["has_authority"]]
        rows.append([f"<td>{chip(label, color)}</td>", f"<td><b>{esc(c['person'])}</b></td>",
                     f"<td>{esc(c['claim'])}</td>", f'<td class="muted">{esc(c["basis"])}</td>'])
    html_block(table(["Status", "Actor", "Action / claim", "Basis"], rows))


def show_contradictions(r) -> None:
    if not r["contradictions"]:
        html_block('<div class="vx-empty">No contradictions found.</div>')
        return
    items = sorted(r["contradictions"], key=lambda c: SEVERITY_ORDER.index(c["severity"]))
    html_block(table(
        ["Severity", "Scope", "Statements", "Explanation"],
        [[f"<td>{chip(c['severity'], SEVERITY_COLOR[c['severity']])}</td>", f'<td class="muted">{esc(c["scope"])}</td>',
          f"<td>“{esc(c['statement_a'])}”<br><span class='vx-muted'>vs</span> “{esc(c['statement_b'])}”</td>",
          f'<td class="muted">{esc(c["explanation"])}</td>'] for c in items],
    ))


def show_raw(report, meta) -> None:
    payload = {"run": meta, "report": report}
    st.download_button(
        "Export report (JSON)", json.dumps(payload, indent=2, default=str),
        file_name=f"veritas-report-{meta['run_id']}.json", mime="application/json",
    )
    st.json(report, expanded=False)


# ---- page -------------------------------------------------------------------
render_sidebar()
html_block('<div class="vx-crumb">Reviews / <b>New review</b></div>'
           '<div class="vx-h1">Document review</div>'
           '<div class="vx-sub">Four agents check structure, factual claims, authority to act, and internal consistency in parallel.</div>')

with st.container(border=True):
    document = st.text_area("Document", key="document", height=240,
                            placeholder="Paste a bill, resolution, or article, or load a sample from the sidebar…")
    run_col, info_col = st.columns([1, 5], vertical_alignment="center")
    run = run_col.button("Run review", type="primary", disabled=not document.strip(), use_container_width=True)
    info_col.caption(f"{len(document):,} characters" + (" · long documents are truncated for the LLM" if len(document) > llm.MAX_DOC_CHARS else ""))

if run:
    with st.spinner(f"Running {len(AGENT_NODES)} agents…"):
        start = time.perf_counter()
        st.session_state["report"] = get_graph().invoke({"document": document})["report"]
        st.session_state["meta"] = {
            "run_id": uuid.uuid4().hex[:8],
            "elapsed": time.perf_counter() - start,
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "model": os.environ.get("SNOWFLAKE_MODEL") or llm.DEFAULT_MODEL,
        }

report, meta = st.session_state.get("report"), st.session_state.get("meta")
if report and meta:
    render_banner(report, meta)
    render_kpis(report)
    sections = [
        ("Overview", "evaluation", "evaluation", show_overview),
        ("Claims", "claim_verification", "claim_verification", show_claims),
        ("Authority", "authority_check", "authority_check", show_authority),
        ("Contradictions", "contradictions", "contradiction", show_contradictions),
    ]
    tabs = st.tabs([s[0] for s in sections] + ["Raw JSON"])
    for tab, (_, key, agent, render) in zip(tabs, sections):
        with tab:
            if report[key] is not None:
                render(report[key])
            else:
                agent_error(report, agent)
    with tabs[-1]:
        show_raw(report, meta)
