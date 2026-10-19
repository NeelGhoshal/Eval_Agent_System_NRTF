# Eval Agent System (LangGraph)

Four agents, each owned by one team member, wired together as a LangGraph.

```
src/eval_system/
  state.py                 shared state + each agent's output contract
  graph.py                 edges between agents (the only place wiring lives)
  agents/
    evaluation/            Evaluation Agent        -> state["evaluation"]
    claim_verification/    Verifying Claims Agent  -> state["claim_verification"]
    authority_check/       Legitimate Authority    -> state["authority_check"]
    contradiction/         Contradiction Agent     -> state["contradictions"]
      agent.py             node function + logic
      prompts.py           prompts for that agent
```

Flow: START -> 4 agents in parallel -> `aggregate` -> END.

## Run
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cd src && python -m eval_system path/to/doc.txt
```

## Working on an agent
Edit only your folder (`agent.py`, `prompts.py`). Keep the node signature
`def x_node(state: EvalState) -> dict` and return only your own state key. If your output
shape changes, update its type in `state.py` and tell the others. All agents are stubs
for now (marked `TODO`).

## LLM (Snowflake Cortex)
All agents call one function, `src/eval_system/llm.py::snowflake_llm` (or `snowflake_json`), which posts to
Snowflake's Cortex `inference:complete` REST endpoint. Set:
```
SNOWFLAKE_ACCOUNT=<account-url-prefix>   # https://<this>.snowflakecomputing.com
SNOWFLAKE_TOKEN=<programmatic access token>
SNOWFLAKE_MODEL=<optional model name>    # default mistral-large2
```
Without these the agents fall back to stubs. `agents/evaluation/agent.py` is a working example.

## Web app (Streamlit)
```
cd src && streamlit run app.py     # http://localhost:8501
```
`src/app.py` is the whole UI; it calls the LangGraph directly.

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. On https://share.streamlit.io: New app > pick the repo, branch `main`, main file `src/app.py`.
3. Under the app's Secrets settings add `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_TOKEN` (and optionally `SNOWFLAKE_MODEL`) as TOML, never in the repo.
