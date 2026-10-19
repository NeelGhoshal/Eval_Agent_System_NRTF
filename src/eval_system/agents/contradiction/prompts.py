SEVERITY_GUIDE = """Severity:
- low: minor wording or rounding inconsistency
- medium: noticeable inconsistency that could confuse a reader
- high: conflicting facts that undermine a significant point
- critical: direct contradiction of a core claim or conclusion"""

INTERNAL_PROMPT = """Find statements WITHIN this document that contradict each other
(conflicting numbers, dates, facts, or conclusions). Quote the two statements verbatim.
{severity_guide}

Document:
\"\"\"
{document}
\"\"\"

Return JSON: {{"contradictions": [{{"statement_a": "...", "statement_b": "...",
"severity": "low|medium|high|critical", "explanation": "why they conflict"}}]}}
Return an empty list if there are none."""

KEY_STATEMENTS_PROMPT = """Pick the {n} most important factual statements in this document that
could conflict with outside sources. Quote them verbatim.

Document:
\"\"\"
{document}
\"\"\"

Return JSON: {{"statements": ["...", "..."]}}"""

EXTERNAL_PROMPT = """Document statement: {statement}

Related outside sources:
{results}

Do any of the sources contradict the statement? Judge ONLY from the sources.
{severity_guide}

Return JSON: {{"contradicts": true | false, "statement_b": "the conflicting text from the source",
"source_index": index of that source or null, "severity": "low|medium|high|critical",
"explanation": "why they conflict"}}"""
