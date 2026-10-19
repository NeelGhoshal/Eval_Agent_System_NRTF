"""Sentry error reporting. No-op unless SENTRY_DSN is set (env var, .env, or Streamlit secrets).

Agent failures are logged with logging.exception (graph.py), which Sentry's logging integration
turns into events; warnings (e.g. a failed LLM attempt) become breadcrumbs on those events.

Config:
  SENTRY_DSN                 project DSN (Sentry > Settings > Projects > <project> > Client Keys)
  SENTRY_ENVIRONMENT         optional, default "local"
  SENTRY_TRACES_SAMPLE_RATE  optional, 0.0-1.0 performance tracing, default 0 (off)
"""
import os

import sentry_sdk

_initialized = False


def init_sentry() -> bool:
    """Initialize once; returns True if Sentry is active."""
    global _initialized
    dsn = os.environ.get("SENTRY_DSN")
    if _initialized or not dsn:
        return _initialized
    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT") or "local",
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE") or 0),
        send_default_pii=False,
        include_local_variables=False,  # stack frames would otherwise carry the pasted document text
    )
    _initialized = True
    return True
