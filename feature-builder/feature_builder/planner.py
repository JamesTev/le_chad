"""
Stage 3: Generate an implementation plan for a relevant HN discovery.
Takes an idea + product context and produces a concrete plan with file changes.
"""

from .llm import chat_json
from .hn import HNStory

PLAN_SYSTEM_PROMPT = """\
You are a senior software engineer. You receive:
1. A PRODUCT CONTEXT describing a software product (its code, stack, gaps).
2. A DISCOVERY from Hacker News — a tool, library, technique, or product idea that is relevant to the product.

Your job: produce a concrete implementation plan to improve the product based on this discovery.

Rules:
- Focus on ONE small, well-scoped improvement. Do NOT try to rewrite the whole product.
- Be specific about which files to change and what the change looks like.
- The plan should be achievable in a single PR (max ~100 lines of code changed).
- Prefer bug fixes, performance improvements, or small features over large new features.

Respond with a JSON object:
{
  "title": "<short PR-style title, e.g. 'Fix N+1 query in task list endpoint'>",
  "summary": "<2-3 sentence description of what this change does and why>",
  "inspired_by": "<title of the HN post that inspired this>",
  "changes": [
    {
      "file": "<relative path to file to change>",
      "action": "modify" | "create",
      "description": "<what to change in this file, be specific>"
    }
  ],
  "test_command": "<shell command to verify the change works, e.g. 'curl http://localhost:8000/tasks'>",
  "risk": "low" | "medium" | "high"
}"""


def generate_plan(story: HNStory, relevance_info: dict, product_context: str) -> dict:
    """Generate an implementation plan for a single discovery."""
    user_msg = (
        f"## PRODUCT CONTEXT\n\n{product_context}\n\n"
        f"## DISCOVERY\n\n"
        f"**Title:** {story.title}\n"
        f"**URL:** {story.url or story.hn_url}\n"
        f"**HN Score:** {story.score} points, {story.num_comments} comments\n"
        f"**Category:** {relevance_info.get('category', 'other')}\n"
        f"**Why relevant:** {relevance_info.get('reason', 'n/a')}\n"
    )
    if story.text:
        cleaned = story.text.replace("<p>", "\n").replace("</p>", "")[:500]
        user_msg += f"**Description:** {cleaned}\n"

    result = chat_json(PLAN_SYSTEM_PROMPT, user_msg)
    result["story_id"] = story.id
    result["story_title"] = story.title
    result["hn_url"] = story.hn_url
    return result
