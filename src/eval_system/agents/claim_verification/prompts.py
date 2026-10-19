EXTRACT_CLAIMS_PROMPT = """Extract the most important verifiable factual claims from this document
(statistics, dates, named events, attributions, scientific or legal assertions). Skip opinions.
Return at most {max_claims} claims, each rewritten to be self-contained.

Document:
\"\"\"
{document}
\"\"\"

Return JSON: {{"claims": ["...", "..."]}}"""

VERIFY_CLAIM_SYSTEM = """You verify claims using ONLY the search results provided; never rely on memory.
Verdicts:
- supported: the results clearly back the claim
- contradicted: the results clearly say otherwise
- unsupported: results are on topic but do not back the claim
- unverifiable: results are missing or irrelevant"""

VERIFY_CLAIM_PROMPT = """Claim: {claim}

Search results:
{results}

Return JSON: {{"verdict": "supported|contradicted|unsupported|unverifiable",
"source_indices": [indices of the results you relied on], "notes": "one or two sentences"}}"""
