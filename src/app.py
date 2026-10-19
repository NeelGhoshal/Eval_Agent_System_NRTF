"""Streamlit UI. Local: cd src && streamlit run app.py"""
import os
import time
import tomllib
from pathlib import Path

import streamlit as st

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

SEVERITY_ICON = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
SEVERITY_ORDER = ["critical", "high", "medium", "low"]
VERDICT_ICON = {"supported": "✅", "contradicted": "❌", "unsupported": "⚠️", "unverifiable": "❔"}
AUTHORITY_STATUS = {True: ("✅", "authorized"), False: ("❌", "not authorized"), None: ("❔", "undetermined")}
DOC_TYPE_LABEL = {"nc_bill": "NC bill", "generic": "Generic document"}

# Demo documents (src/demo_data/samples), label -> file
SAMPLES_DIR = Path(__file__).parent / "demo_data" / "samples"
SAMPLES = {
    "NC Senate Bill 2 (complete)": "s2_complete.txt",
    "NC Senate Bill 2 (sponsor, fiscal, effective date removed)": "s2_flawed.txt",
    "News article (illustrative, no sources)": "news_article.txt",
}
PASTE_OWN = "Paste your own..."

st.set_page_config(page_title="Eval Agent System", layout="wide")


@st.cache_resource
def get_graph():
    return build_graph()


def load_sample():
    choice = st.session_state["sample"]
    if choice != PASTE_OWN:
        st.session_state["document"] = (SAMPLES_DIR / SAMPLES[choice]).read_text(encoding="utf-8")


# ---- per-agent renderers ------------------------------------------------------
def show_evaluation(e):
    left, right = st.columns([1, 3])
    left.metric("Overall score", f"{e['overall_score']:.2f}")
    left.markdown(f"**Type:** `{DOC_TYPE_LABEL.get(e.get('doc_type'), e.get('doc_type', '?'))}`")
    right.progress(min(max(e["overall_score"], 0.0), 1.0))
    cols = right.columns(max(len(e["criteria_scores"]), 1))
    for col, (name, score) in zip(cols, e["criteria_scores"].items()):
        col.metric(name.capitalize(), "n/a" if score is None else f"{score:.2f}")
    st.caption(e["summary"])

    findings = e.get("findings", [])
    st.subheader("Findings")
    if not findings:
        st.caption("No findings.")
    for sev in SEVERITY_ORDER:
        group = [f for f in findings if f["severity"] == sev]
        if group:
            st.markdown(f"**{SEVERITY_ICON[sev]} {sev.capitalize()} ({len(group)})**")
        for f in group:
            st.markdown(f"- `{f['code']}` — {f['message']}")
            if f.get("evidence"):
                st.caption(f["evidence"])


def show_claims(r):
    if not r["checks"]:
        st.caption("No claims checked.")
    for c in r["checks"]:
        with st.container(border=True):
            st.markdown(f"{VERDICT_ICON.get(c['verdict'], '•')} **{c['verdict']}** — {c['claim']}")
            if c["notes"]:
                st.caption(c["notes"])
            for s in c["sources"]:
                st.markdown(f"- {s}")


def show_authority(r):
    if not r["checks"]:
        st.caption("No authorities checked.")
    for c in r["checks"]:
        icon, status = AUTHORITY_STATUS[c["has_authority"]]
        with st.container(border=True):
            st.markdown(f"{icon} **{c['person']}** — {status}")
            st.write(c["claim"])
            st.caption(c["basis"])


def show_contradictions(r):
    if not r["contradictions"]:
        st.caption("No contradictions found.")
    for c in r["contradictions"]:
        with st.container(border=True):
            st.markdown(f"{SEVERITY_ICON[c['severity']]} **{c['severity']}** ({c['scope']})")
            st.write(f"“{c['statement_a']}” vs “{c['statement_b']}”")
            st.caption(c["explanation"])


def show_summary(report):
    """Top row: one headline number per agent ("—" if the agent failed)."""
    e, cv, au, co = (report[k] for k in ("evaluation", "claim_verification", "authority_check", "contradictions"))
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Overall score", f"{e['overall_score']:.2f}" if e else "—")
    if e:
        worst = next((s for s in SEVERITY_ORDER if any(f["severity"] == s for f in e["findings"])), None)
        c2.metric("Findings", len(e["findings"]), f"worst: {worst}" if worst else "none", delta_color="off")
    else:
        c2.metric("Findings", "—")
    if cv:
        supported = sum(c["verdict"] == "supported" for c in cv["checks"])
        c3.metric("Claims supported", f"{supported}/{len(cv['checks'])}")
    else:
        c3.metric("Claims supported", "—")
    if au:
        authorized = sum(c["has_authority"] is True for c in au["checks"])
        c4.metric("Authority checks", len(au["checks"]), f"{authorized} authorized", delta_color="off")
    else:
        c4.metric("Authority checks", "—")
    c5.metric("Contradictions", len(co["contradictions"]) if co else "—")


# ---- page -------------------------------------------------------------------
st.title("Eval Agent System")
st.write(
    "Four agents review a document in parallel: **Evaluation** (structure and quality), "
    "**Claim verification** (facts vs. sources), **Authority check** (who may act), and **Contradictions**."
)

st.selectbox("Load sample", [PASTE_OWN, *SAMPLES], key="sample", on_change=load_sample)
document = st.text_area("Document", key="document", height=260, placeholder="Paste document text here...")

if st.button("Evaluate", type="primary", disabled=not document.strip()):
    with st.spinner(f"Running {len(AGENT_NODES)} agents..."):
        start = time.perf_counter()
        st.session_state["report"] = get_graph().invoke({"document": document})["report"]
        st.session_state["elapsed"] = time.perf_counter() - start

report = st.session_state.get("report")
if report:
    st.divider()
    st.caption(f"Ran {len(AGENT_NODES)} agents in {st.session_state.get('elapsed', 0):.1f}s")
    show_summary(report)
    sections = [
        ("Evaluation", "evaluation", "evaluation", show_evaluation),
        ("Claims", "claim_verification", "claim_verification", show_claims),
        ("Authority", "authority_check", "authority_check", show_authority),
        ("Contradictions", "contradictions", "contradiction", show_contradictions),
    ]
    for tab, (title, key, agent, render) in zip(st.tabs([s[0] for s in sections]), sections):
        with tab:
            if report[key] is not None:
                render(report[key])
            else:
                st.error(report["errors"].get(agent, "No result."))
