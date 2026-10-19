"""The single LLM entry point for every agent (Snowflake Cortex REST API).

All agents call `snowflake_llm` / `snowflake_json`; to switch models or providers,
change this file (or SNOWFLAKE_MODEL) only.

Config (env vars, a gitignored .env at the repo root, or Streamlit secrets, see app.py):
  SNOWFLAKE_ACCOUNT      account URL prefix, e.g. "myorg-myaccount" -> https://myorg-myaccount.snowflakecomputing.com
  SNOWFLAKE_MODEL        optional, default below
  SNOWFLAKE_WAREHOUSE    optional, for the SQL API fallback used when the REST endpoint is blocked
  Auth, either:
  SNOWFLAKE_USER +
  SNOWFLAKE_PRIVATE_KEY  key-pair auth (preferred: needs no network policy). Set up with
                         `python setup_snowflake.py` from src/.
  SNOWFLAKE_TOKEN        or a programmatic access token (requires a network policy on the user)

Smoke test (from src/):  python -m eval_system.llm
"""
import base64
import hashlib
import json
import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()  # local dev only; never overrides vars already set (e.g. from Streamlit secrets)

DEFAULT_MODEL = "claude-sonnet-4-5"  # any model enabled for your account/region (mistral-large2 is retired)
DEFAULT_WAREHOUSE = "SNOWFLAKE_LEARNING_WH"  # only used by the SQL API fallback


class LLMNotConfigured(RuntimeError):
    pass


def is_configured() -> bool:
    has_keypair = os.environ.get("SNOWFLAKE_USER") and os.environ.get("SNOWFLAKE_PRIVATE_KEY")
    return bool(os.environ.get("SNOWFLAKE_ACCOUNT") and (has_keypair or os.environ.get("SNOWFLAKE_TOKEN")))


_jwt_cache: dict = {"token": None, "exp": 0}


def _keypair_jwt() -> str:
    """Snowflake key-pair JWT: https://docs.snowflake.com/en/developer-guide/sql-api/authenticating"""
    if _jwt_cache["token"] and _jwt_cache["exp"] - time.time() > 300:
        return _jwt_cache["token"]
    import jwt
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(os.environ["SNOWFLAKE_PRIVATE_KEY"].encode(), password=None)
    public_der = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(public_der).digest()).decode()
    qualified_user = f"{os.environ['SNOWFLAKE_ACCOUNT'].split('.')[0].upper()}.{os.environ['SNOWFLAKE_USER'].upper()}"
    now = int(time.time())
    exp = now + 3540  # Snowflake caps JWT lifetime at 1 hour
    token = jwt.encode(
        {"iss": f"{qualified_user}.{fingerprint}", "sub": qualified_user, "iat": now, "exp": exp},
        key,
        algorithm="RS256",
    )
    _jwt_cache.update(token=token, exp=exp)
    return token


def _auth_headers() -> dict:
    if os.environ.get("SNOWFLAKE_PRIVATE_KEY") and os.environ.get("SNOWFLAKE_USER"):
        return {"Authorization": f"Bearer {_keypair_jwt()}", "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT"}
    return {
        "Authorization": f"Bearer {os.environ['SNOWFLAKE_TOKEN']}",
        "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
    }


def _base_url() -> str:
    return f"https://{os.environ['SNOWFLAKE_ACCOUNT']}.snowflakecomputing.com"


def _headers() -> dict:
    return {**_auth_headers(), "Content-Type": "application/json", "Accept": "application/json"}


# Some accounts (e.g. trials) get 403 "not allowed to access this endpoint" from the Cortex REST API
# but can still call Cortex via SQL. After the first such 403, every call goes through SQL.
_REST_BLOCKED = '"code":"003001"'
_transport = {"sql": False}


def _complete_rest(messages: list, model: str) -> str:
    r = requests.post(
        f"{_base_url()}/api/v2/cortex/inference:complete",
        timeout=60,
        headers=_headers(),
        json={"model": model, "messages": messages, "stream": False},
    )
    if r.status_code == 403 and _REST_BLOCKED in r.text.replace(" ", ""):
        _transport["sql"] = True
        return _complete_sql(messages, model)
    if not r.ok:  # surface Snowflake's own message (e.g. "Network policy is required")
        raise RuntimeError(f"Snowflake {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


def _complete_sql(messages: list, model: str) -> str:
    """SNOWFLAKE.CORTEX.COMPLETE through the SQL API (needs a warehouse: SNOWFLAKE_WAREHOUSE)."""
    url = f"{_base_url()}/api/v2/statements"
    r = requests.post(
        url,
        timeout=90,
        headers=_headers(),
        json={
            "statement": "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, PARSE_JSON(?), {})",
            "bindings": {
                "1": {"type": "TEXT", "value": model},
                "2": {"type": "TEXT", "value": json.dumps(messages)},
            },
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE") or DEFAULT_WAREHOUSE,
            "timeout": 120,
        },
    )
    deadline = time.time() + 120
    while r.status_code == 202 and time.time() < deadline:  # still running: poll the statement handle
        time.sleep(1)
        r = requests.get(f"{url}/{r.json()['statementHandle']}", timeout=30, headers=_headers())
    if r.status_code != 200:
        raise RuntimeError(f"Snowflake SQL {r.status_code}: {r.text[:300]}")
    return json.loads(r.json()["data"][0][0])["choices"][0]["messages"]


def snowflake_llm(prompt: str, system: str = "", model: str | None = None) -> str:
    if not is_configured():
        raise LLMNotConfigured("Set SNOWFLAKE_ACCOUNT plus SNOWFLAKE_USER/SNOWFLAKE_PRIVATE_KEY (or SNOWFLAKE_TOKEN).")
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    model = model or os.environ.get("SNOWFLAKE_MODEL") or DEFAULT_MODEL  # empty env var = default
    return (_complete_sql if _transport["sql"] else _complete_rest)(messages, model)


def snowflake_json(prompt: str, system: str = "", model: str | None = None):
    """Like snowflake_llm, but parses a JSON object/array out of the reply."""
    text = snowflake_llm(prompt, system + "\nRespond with valid JSON only.", model)
    match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)  # tolerate ```json fences / chatter
    if not match:
        raise ValueError(f"No JSON in model reply: {text[:200]!r}")
    return json.loads(match.group(0))


MAX_DOC_CHARS = 15_000


def clip(text: str, limit: int = MAX_DOC_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + " [...document truncated...]"


if __name__ == "__main__":
    # Reads src/.streamlit/secrets.toml too, so this works with the same config as the app.
    import tomllib
    from pathlib import Path

    secrets = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
    if secrets.exists():
        for k, v in tomllib.loads(secrets.read_text(encoding="utf-8")).items():
            os.environ.setdefault(k, str(v))
    print(snowflake_llm("Reply with exactly: Snowflake Cortex is working."))
