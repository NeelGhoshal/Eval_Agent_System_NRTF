"""The single LLM entry point for every agent (Snowflake Cortex REST API).

All agents call `snowflake_llm` / `snowflake_json`; to switch models or providers,
change this file (or SNOWFLAKE_MODEL) only.

Config (env vars, a gitignored .env at the repo root, or Streamlit secrets, see app.py):
  SNOWFLAKE_ACCOUNT  account URL prefix, e.g. "myorg-myaccount" -> https://myorg-myaccount.snowflakecomputing.com
  SNOWFLAKE_TOKEN    programmatic access token (PAT), JWT, or OAuth token
  SNOWFLAKE_MODEL    optional, default below
"""
import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()  # local dev only; never overrides vars already set (e.g. from Streamlit secrets)

DEFAULT_MODEL = "mistral-large2"  # any model enabled for your account/region


class LLMNotConfigured(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("SNOWFLAKE_ACCOUNT") and os.environ.get("SNOWFLAKE_TOKEN"))


def snowflake_llm(prompt: str, system: str = "", model: str | None = None) -> str:
    if not is_configured():
        raise LLMNotConfigured("Set SNOWFLAKE_ACCOUNT and SNOWFLAKE_TOKEN.")
    url = f"https://{os.environ['SNOWFLAKE_ACCOUNT']}.snowflakecomputing.com/api/v2/cortex/inference:complete"
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    r = requests.post(
        url,
        timeout=60,
        headers={
            "Authorization": f"Bearer {os.environ['SNOWFLAKE_TOKEN']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "model": model or os.environ.get("SNOWFLAKE_MODEL", DEFAULT_MODEL),
            "messages": messages,
            "stream": False,
        },
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def snowflake_json(prompt: str, system: str = "", model: str | None = None):
    """Like snowflake_llm, but parses a JSON object/array out of the reply."""
    text = snowflake_llm(prompt, system + "\nRespond with valid JSON only.", model)
    match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)  # tolerate ```json fences / chatter
    if not match:
        raise ValueError(f"No JSON in model reply: {text[:200]!r}")
    return json.loads(match.group(0))
