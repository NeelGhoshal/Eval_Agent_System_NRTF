EXTRACT_PEOPLE_PROMPT = """List the people and organizations in this document who make claims,
give opinions, or are cited as authorities (authors, quoted experts, officials, institutions).
For each, give the role the document gives them and the main claim they make or are responsible for.
At most {max_actors} entries.

Document:
\"\"\"
{document}
\"\"\"

Return JSON: {{"actors": [{{"person": "name", "role": "role stated in the document or empty", "claim": "..."}}]}}"""

AUTHORITY_SYSTEM = """You judge whether a person or organization has legitimate authority to make a claim:
relevant credentials, expertise, official role, jurisdiction, or legal right.
Use ONLY the document context and the search results provided. If the evidence is insufficient,
answer null rather than guessing. Authority is about standing to make THIS claim, not whether the claim is true."""

AUTHORITY_PROMPT = """Person/organization: {person}
Role stated in document: {role}
Claim: {claim}

Search results about this person:
{results}

Return JSON: {{"has_authority": true | false | null, "basis": "one or two sentences naming the credentials, role or gap"}}"""
