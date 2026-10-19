JUDGE_SYSTEM = """You are a strict reviewer of document quality. You judge only HOW a document is
written, never whether its claims are true or whether its authors had authority to act.
Score with whole numbers 0-5 and be consistent: the same document must get the same scores."""

# Filled with str.format(doc_type=..., document=...); literal braces are doubled.
JUDGE_PROMPT = """Document type: {doc_type}

Score this document on two dimensions (integers 0-5):

provenance: Does it cite traceable sources or references (statutes, bill numbers, session laws,
reports, links, named documents, dated records)? Judge traceability only, not whether they are true.
  0 = no sources at all, 1-2 = vague ("officials say", "studies show"),
  3 = some specific references, 4 = most statements traceable, 5 = fully referenced.

clarity: Is the action or purpose specific (who does what, by when, with what money/effect)?
  0 = cannot tell what it does, 1-2 = vague or generic language,
  3 = main action clear but key details missing, 4 = specific, 5 = precise and unambiguous.

Return exactly this JSON object:
{{"provenance": <0-5>, "clarity": <0-5>,
  "provenance_reason": "<one sentence>", "clarity_reason": "<one sentence>"}}

Document:
\"\"\"
{document}
\"\"\""""
