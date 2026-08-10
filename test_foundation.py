"""
Requires GOOGLE_API_KEY set in .env
"""

from schemas import ParsedIdea
from llm_client import call_structured

PROMPT = """
Extract structured info from this project idea and return it as JSON matching
the required schema.

Idea: "I want to build an app that recommends recipes based on what's left in
your fridge, aimed at solo students on a tight budget. I have 3 months and I'm
building it alone, I know Python but I'm new to ML."

Fields to fill:
- raw_text: the idea text verbatim
- domain: the industry/domain
- scale: intended scale
- constraints.budget, constraints.timeline, constraints.team_size
- technical_maturity: one of beginner/intermediate/advanced
- summary: 1-2 sentence normalized summary
"""

if __name__ == "__main__":
    result = call_structured(PROMPT, ParsedIdea)
    print(result.model_dump_json(indent=2))
