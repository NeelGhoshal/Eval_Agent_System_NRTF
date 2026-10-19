"""Streamlit UI. Local: cd src && streamlit run app.py"""
import os

import streamlit as st

from eval_system.graph import AGENT_NODES, build_graph
from eval_system.llm import is_configured

# On Streamlit Cloud, credentials come from the app's Secrets; locally from env vars.
for _key in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_TOKEN", "SNOWFLAKE_MODEL"):
    try:
        if _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
    except Exception:  # no secrets file locally
        pass

SEVERITY_ICON = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}

st.set_page_config(page_title="Eval Agent System", layout="centered")


@st.cache_resource
def get_graph():
    return build_graph()


def show_evaluation(e):
    st.metric("Overall score", f"{e['overall_score']:.2f}")
    st.dataframe(
        {"criterion": list(e["criteria_scores"]), "score": list(e["criteria_scores"].values())},
        hide_index=True,
        use_container_width=True,
    )
    st.caption(e["summary"])


def show_claims(r):
    if not r["checks"]:
        st.caption("No claims checked.")
    for c in r["checks"]:
        st.markdown(f"**{c['verdict']}** — {c['claim']}")
        st.caption(c["notes"])
        for s in c["sources"]:
            st.markdown(f"- {s}")


def show_authority(r):
    if not r["checks"]:
        st.caption("No authorities checked.")
    for c in r["checks"]:
        status = {None: "undetermined", True: "authorized", False: "not authorized"}[c["has_authority"]]
        st.markdown(f"**{c['person']}** — {status}")
        st.write(c["claim"])
        st.caption(c["basis"])


def show_contradictions(r):
    if not r["contradictions"]:
        st.caption("No contradictions found.")
    for c in r["contradictions"]:
        st.markdown(f"{SEVERITY_ICON[c['severity']]} **{c['severity']}** ({c['scope']})")
        st.write(f"“{c['statement_a']}” vs “{c['statement_b']}”")
        st.caption(c["explanation"])


st.title("Eval Agent System")
if not is_configured():
    st.warning("Snowflake LLM not configured (set SNOWFLAKE_ACCOUNT and SNOWFLAKE_TOKEN); agents run as stubs.")
st.write("Paste a document. Four agents evaluate quality, verify claims, check authority, and find contradictions.")

document = st.text_area("Document", height=220, placeholder="Paste document text here...")

if st.button("Evaluate", type="primary", disabled=not document.strip()):
    with st.spinner(f"Running {len(AGENT_NODES)} agents..."):
        st.session_state["report"] = get_graph().invoke({"document": document})["report"]

report = st.session_state.get("report")
if report:
    sections = [
        ("Evaluation", "evaluation", show_evaluation),
        ("Claim verification", "claim_verification", show_claims),
        ("Authority check", "authority_check", show_authority),
        ("Contradictions", "contradictions", show_contradictions),
    ]
    for title, key, render in sections:
        with st.expander(title, expanded=True):
            render(report[key])
