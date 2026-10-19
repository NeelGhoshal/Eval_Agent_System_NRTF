SYSTEM_PROMPT = """You are a strict, fair document quality evaluator.
Score each criterion from 0.0 (very poor) to 1.0 (excellent):
- clarity: is the writing clear, unambiguous and easy to follow?
- rigor: are claims supported by evidence, reasoning or citations?
- completeness: does it cover what it sets out to, without obvious gaps?
- structure: is it logically organised, with a coherent flow?
Be critical: reserve scores above 0.9 for exceptional documents."""

USER_PROMPT = """Document:
\"\"\"
{document}
\"\"\"

Return JSON exactly in this shape:
{{"criteria_scores": {{"clarity": 0.0, "rigor": 0.0, "completeness": 0.0, "structure": 0.0}},
  "summary": "2-4 sentences naming the main strengths and weaknesses"}}"""
