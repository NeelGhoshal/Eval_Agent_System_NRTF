# Veritas

**Document integrity review.** Paste a bill, resolution, or article and four AI agents check it in parallel:
structure, factual claims, authority to act, and internal consistency. Built for the ATO Hackathon with
LangGraph, Snowflake Cortex, and Streamlit.

| Agent | Question it answers | How |
|---|---|---|
| Evaluation | Is the document complete, sourced, and clear? | Rule-based completeness rubric + LLM judge |
| Claim Verification | Are its factual claims true? | Extracts claims, web-searches each, LLM verdict with real source URLs |
| Authority Check | Do the people in it have standing to act? | Extracts actors and claims, web-searches each, LLM judges standing |
| Contradiction | Does it contradict itself or outside sources? | Internal LLM pass + web-checked key statements, rated by severity |

## Quick start
Needs Python 3.11+ and a Snowflake account with Cortex enabled.

1. Install:
   ```
   git clone https://github.com/NeelGhoshal/Eval_Agent_System_NRTF.git
   cd Eval_Agent_System_NRTF
   python -m venv .venv
   .venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Connect Snowflake (one time, from `src/`):
   ```
   cd src
   python setup_snowflake.py         # writes src/.streamlit/secrets.toml, prints one SQL command
   ```
   Run the printed `ALTER USER ... SET RSA_PUBLIC_KEY='...'` in a Snowsight worksheet as ACCOUNTADMIN,
   then check it with `python -m eval_system.llm`.
3. Turn on error monitoring (optional): add `SENTRY_DSN = "..."` to `src/.streamlit/secrets.toml`
   (see [Error monitoring](#error-monitoring-sentry)).
4. Run the app:
   ```
   streamlit run app.py              # http://localhost:8501
   ```
   Pick a sample from the sidebar (e.g. *NC Senate Bill 2*) and click **Run review**.

The sidebar's **System status** shows whether the LLM and Sentry are connected.

## Screenshots
A review of NC Senate Bill 2 ("Relief at the Pump"), one section per agent.

**Overview and Evaluation Agent**: verdict banner, one headline card per agent, and the
evaluation's quality criteria (completeness, provenance, clarity) with its summary.

![Overview: verdict, KPI cards, and Evaluation Agent criteria](docs/screenshots/overview-evaluation.png)

**Claim Verification Agent**: each factual claim with a verdict, the reasoning, and the sources found.

![Claims tab: verdicts with sources](docs/screenshots/claims.png)

**Authority Check Agent**: each actor in the bill, whether they have standing to act, and why.

![Authority tab: actors and their basis](docs/screenshots/authority.png)

**Contradiction Agent**: conflicting statements within the document, rated by severity.

![Contradictions tab: conflicting sections with severity](docs/screenshots/contradictions.png)

## Configuration
Put settings in `src/.streamlit/secrets.toml` (TOML: `KEY = "value"`) or a `.env` at the repo root
(`KEY=value`). Both are gitignored; never commit them. Environment variables take precedence.

| Key | Required | Purpose |
|---|---|---|
| `SNOWFLAKE_ACCOUNT` | yes | Account identifier, e.g. `myorg-myaccount` |
| `SNOWFLAKE_USER` + `SNOWFLAKE_PRIVATE_KEY` | yes, or token | Key-pair auth (preferred, no network policy needed); set by `setup_snowflake.py` |
| `SNOWFLAKE_TOKEN` | or this | Programmatic access token instead of key pair (needs a network policy on the user) |
| `SNOWFLAKE_MODEL` | no | Cortex model, default `claude-sonnet-4-5` (`mistral-large2` is retired) |
| `SNOWFLAKE_WAREHOUSE` | no | Warehouse for the SQL API fallback, used if the REST endpoint is blocked |
| `SENTRY_DSN` | no | Turns on Sentry error reporting |
| `SENTRY_ENVIRONMENT` | no | Environment tag in Sentry, default `local` |
| `SENTRY_TRACES_SAMPLE_RATE` | no | 0.0-1.0 performance tracing, default `0` (off) |

Web search uses DuckDuckGo and needs no key.

## Error monitoring (Sentry)
Agent failures (a bad LLM reply, a network error) are reported to the Sentry project
`lumigrid/eval-agent-system`, with the stack trace, environment, and git commit. One failing agent
never stops the others; its tab shows "Agent unavailable" and the report lists the error.

- **Get the DSN:** Sentry > `eval-agent-system` > Settings > Client Keys (DSN).
- **Set it:** `SENTRY_DSN = "https://...ingest.us.sentry.io/..."` in `secrets.toml` (or `.env`). Without it,
  Sentry stays off and nothing is sent.
- **Privacy:** local variables and personal data are excluded, so the pasted document isn't attached to
  events. An error message can still quote up to 200 characters of a malformed model reply.

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. On https://share.streamlit.io: **New app** > pick the repo, branch `main`, main file `src/app.py`.
3. In the app's **Settings > Secrets**, paste your local `src/.streamlit/secrets.toml` and add:
   ```
   SENTRY_DSN = "https://...ingest.us.sentry.io/..."
   SENTRY_ENVIRONMENT = "production"
   ```
4. Reboot the app. The sidebar should show **Error monitoring: On**, and errors appear in Sentry tagged
   `production`.

## Command line
Runs the same graph without the UI and prints the JSON report (from `src/`):
```
python -m eval_system demo_data/samples/s2_flawed.txt
```

## Project layout
```
src/
  app.py                   Streamlit UI (Veritas); calls the graph directly
  setup_snowflake.py       one-time Snowflake key-pair setup
  demo_data/samples/       sample documents shown in the sidebar
  eval_system/
    graph.py               edges between agents (the only place wiring lives)
    state.py               shared state + each agent's output contract
    llm.py                 single LLM entry point (Snowflake Cortex)
    observability.py       Sentry setup
    agents/
      evaluation/          Evaluation Agent        -> state["evaluation"]
      claim_verification/  Verifying Claims Agent  -> state["claim_verification"]
      authority_check/     Legitimate Authority    -> state["authority_check"]
      contradiction/       Contradiction Agent     -> state["contradictions"]
        agent.py           node function + logic
        prompts.py         prompts for that agent
```

Flow: START -> 4 agents in parallel -> `aggregate` -> END.

## Working on an agent
Each agent is owned by one team member. Edit only your folder (`agent.py`, `prompts.py`). Keep the node
signature `def x_node(state: EvalState) -> dict` and return only your own state key. If your output shape
changes, update its type in `state.py` and tell the others. All LLM calls go through
`eval_system/llm.py::snowflake_llm` (or `snowflake_json`); to switch models or providers, change that file only.
