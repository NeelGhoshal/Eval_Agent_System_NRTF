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
