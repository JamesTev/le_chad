"""
Hacker News API client + Mistral-powered idea filter.
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass

import httpx
from mistralai.client import Mistral

HN_BASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"


@dataclass
class HNStory:
    id: int
    title: str
    url: str | None
    author: str
    score: int
    text: str | None
    num_comments: int
    story_type: str

    @property
    def hn_url(self) -> str:
        return f"https://news.ycombinator.com/item?id={self.id}"


# ---------- HN fetching ----------


async def fetch_story_ids(
    client: httpx.AsyncClient, feed: str = "top", limit: int = 30
) -> list[int]:
    feeds = {
        "top": f"{HN_BASE}/topstories.json",
        "new": f"{HN_BASE}/newstories.json",
        "best": f"{HN_BASE}/beststories.json",
        "show": f"{HN_BASE}/showstories.json",
        "ask": f"{HN_BASE}/askstories.json",
    }
    resp = await client.get(feeds[feed])
    resp.raise_for_status()
    return resp.json()[:limit]


async def fetch_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    resp = await client.get(f"{HN_BASE}/item/{item_id}.json")
    if resp.status_code != 200:
        return None
    return resp.json()


def _item_to_story(item: dict, feed: str) -> HNStory | None:
    if not item or item.get("type") != "story":
        return None
    return HNStory(
        id=item["id"],
        title=item.get("title", ""),
        url=item.get("url"),
        author=item.get("by", "unknown"),
        score=item.get("score", 0),
        text=item.get("text"),
        num_comments=item.get("descendants", 0),
        story_type=feed,
    )


async def fetch_stories(
    client: httpx.AsyncClient,
    feed: str = "top",
    limit: int = 30,
    min_score: int = 0,
) -> list[HNStory]:
    """Fetch stories from a HN feed, optionally filtering by minimum score."""
    raw_limit = limit * 3 if min_score > 0 else limit
    ids = await fetch_story_ids(client, feed, raw_limit)
    items = await asyncio.gather(*[fetch_item(client, sid) for sid in ids])

    stories = []
    for item in items:
        story = _item_to_story(item, feed)
        if story and story.score >= min_score:
            stories.append(story)
        if len(stories) >= limit:
            break
    return stories


async def fetch_user_stories(
    client: httpx.AsyncClient,
    username: str,
    limit: int = 20,
    min_score: int = 0,
) -> list[HNStory]:
    """Fetch stories by a specific user via Algolia, with optional score filter."""
    params: dict = {
        "tags": f"author_{username},story",
        "hitsPerPage": limit,
    }
    if min_score > 0:
        params["numericFilters"] = f"points>{min_score}"

    resp = await client.get(f"{ALGOLIA_BASE}/search", params=params)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return [
        HNStory(
            id=int(hit.get("objectID", 0)),
            title=hit.get("title", ""),
            url=hit.get("url"),
            author=hit.get("author", username),
            score=hit.get("points", 0),
            text=hit.get("story_text"),
            num_comments=hit.get("num_comments", 0),
            story_type="user_submission",
        )
        for hit in hits
    ]


async def search_stories(
    client: httpx.AsyncClient,
    query: str,
    limit: int = 20,
    min_score: int = 0,
) -> list[HNStory]:
    """Full-text search across HN via Algolia."""
    params: dict = {
        "query": query,
        "tags": "story",
        "hitsPerPage": limit,
    }
    if min_score > 0:
        params["numericFilters"] = f"points>{min_score}"

    resp = await client.get(f"{ALGOLIA_BASE}/search", params=params)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return [
        HNStory(
            id=int(hit.get("objectID", 0)),
            title=hit.get("title", ""),
            url=hit.get("url"),
            author=hit.get("author", "unknown"),
            score=hit.get("points", 0),
            text=hit.get("story_text"),
            num_comments=hit.get("num_comments", 0),
            story_type="search",
        )
        for hit in hits
    ]


# ---------- Mistral shared helpers ----------

COARSE_BATCH_SIZE = 25
RELEVANCE_BATCH_SIZE = 20


def _get_mistral_client() -> Mistral:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("[ERROR] MISTRAL_API_KEY not set. Create a .env file or export it.")
        sys.exit(1)
    return Mistral(api_key=api_key)


def _stories_to_batch_text(stories: list[HNStory]) -> str:
    return "\n".join(
        f"[ID:{s.id}] {s.title}" + (f" | {s.text[:200]}" if s.text else "")
        for s in stories
    )


def _parse_results_json(raw: str, label: str = "LLM") -> list[dict]:
    """Parse a Mistral JSON response, stripping the 'thinking' CoT field from each result."""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "results" in parsed:
            parsed = parsed["results"]
        if isinstance(parsed, dict):
            parsed = list(parsed.values())
        for item in parsed:
            item.pop("thinking", None)
        return parsed
    except json.JSONDecodeError:
        print(f"[WARN] Failed to parse {label} response:\n{raw[:500]}")
        return []


# ---------- Mistral idea filter ----------

FILTER_SYSTEM_PROMPT = """\
You are a product idea filter. You receive a batch of Hacker News story titles (and optional self-text).

For EACH story, think step-by-step then decide:
- "idea": This post describes, demonstrates, or directly inspires a BUILDABLE software product or feature.
  Examples: "Show HN: I built X", product launches, open-source tool announcements,
  "I wish X existed", technical posts that imply a clear product opportunity.
- "noise": Everything else — general news, opinion pieces, hiring posts, meta-discussions,
  questions without a product angle, political/social commentary.

Be aggressive with filtering. We want high-precision "idea" labels — only clear product inspiration.

Respond with a JSON object with a single key "results" containing an array.
Each element: {"id": <story_id>, "thinking": "<your reasoning in 1-2 sentences>", "label": "idea" or "noise", "reason": "<10 words max>"}
IMPORTANT: Always write the "thinking" field BEFORE the "label" field so you reason before deciding.
No markdown, no extra text. Just the JSON object."""


async def _coarse_filter_chunk(client: Mistral, stories: list[HNStory]) -> list[dict]:
    batch_text = _stories_to_batch_text(stories)
    resp = await client.chat.complete_async(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": FILTER_SYSTEM_PROMPT},
            {"role": "user", "content": batch_text},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return _parse_results_json(resp.choices[0].message.content, "coarse filter")


async def coarse_filter(stories: list[HNStory]) -> list[dict]:
    """Classify stories as idea vs noise. Batches into concurrent chunks for speed."""
    if not stories:
        return []

    client = _get_mistral_client()
    chunks = [
        stories[i : i + COARSE_BATCH_SIZE]
        for i in range(0, len(stories), COARSE_BATCH_SIZE)
    ]

    chunk_results = await asyncio.gather(
        *[_coarse_filter_chunk(client, chunk) for chunk in chunks]
    )

    merged: list[dict] = []
    for result in chunk_results:
        merged.extend(result)
    return merged


# ---------- Product-aware relevance filter ----------

RELEVANCE_SYSTEM_PROMPT = """\
You are a product relevance scorer. You receive:
1. A PRODUCT CONTEXT describing a specific software product (its stack, domain, gaps, keywords).
2. A batch of Hacker News stories that have already passed a coarse "is this a product/tool?" filter.

For EACH story, think step-by-step about how it relates to the product, then decide:
- "relevant": This tool, library, MCP, technique, or product could directly improve, integrate with,
  or solve a known gap in the target product. High confidence it's useful.
- "maybe": Tangentially related — same domain, similar tech stack, or addresses a general problem
  the product might face. Worth a look but not a direct fit.
- "noise": Not relevant to this specific product despite being a real tool/idea.

Also assign a category to each:
- "tool" — standalone tool or CLI
- "library" — importable library or framework
- "mcp" — MCP server, plugin, or integration
- "technique" — pattern, architecture approach, or best practice
- "product" — full product or SaaS that could inspire features
- "other" — doesn't fit above

Respond with a JSON object: {"results": [{"id": <story_id>,
"thinking": "<your reasoning about how this relates to the product — 1-3 sentences>",
"label": "relevant"|"maybe"|"noise",
"category": "<category>", "reason": "<15 words max explaining why it's relevant to the product>"}]}
IMPORTANT: Always write "thinking" BEFORE "label" so you reason before deciding.
No markdown, no extra text. Just the JSON object."""


async def _relevance_filter_chunk(
    client: Mistral, stories: list[HNStory], product_context: str
) -> list[dict]:
    batch_text = _stories_to_batch_text(stories)
    user_message = (
        f"## PRODUCT CONTEXT\n\n{product_context}\n\n"
        f"## HN STORIES TO SCORE\n\n{batch_text}"
    )
    resp = await client.chat.complete_async(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": RELEVANCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return _parse_results_json(resp.choices[0].message.content, "relevance filter")


async def relevance_filter(stories: list[HNStory], product_context: str) -> list[dict]:
    """Score pre-filtered stories for product relevance. Batches into concurrent chunks."""
    if not stories:
        return []

    client = _get_mistral_client()
    chunks = [
        stories[i : i + RELEVANCE_BATCH_SIZE]
        for i in range(0, len(stories), RELEVANCE_BATCH_SIZE)
    ]

    chunk_results = await asyncio.gather(
        *[_relevance_filter_chunk(client, chunk, product_context) for chunk in chunks]
    )

    merged: list[dict] = []
    for result in chunk_results:
        merged.extend(result)
    return merged


# ---------- Markdown output ----------


def stories_to_markdown(
    stories: list[HNStory],
    filter_results: list[dict] | None = None,
    title: str = "HN Product Ideas",
) -> str:
    """Render stories (and optional filter results) as a markdown document."""
    lines = [f"# {title}\n"]

    if filter_results:
        result_map = {r["id"]: r for r in filter_results}
        ideas = [s for s in stories if result_map.get(s.id, {}).get("label") == "idea"]
        noise = [s for s in stories if result_map.get(s.id, {}).get("label") == "noise"]

        lines.append(f"**{len(ideas)} ideas** extracted from {len(stories)} stories\n")
        lines.append("## Ideas\n")
        for s in ideas:
            r = result_map.get(s.id, {})
            lines.append(f"### [{s.title}]({s.hn_url})")
            lines.append(
                f"- **Score:** {s.score} | **Comments:** {s.num_comments} | **Author:** @{s.author}"
            )
            if s.url:
                lines.append(f"- **Link:** {s.url}")
            lines.append(f"- **Why:** {r.get('reason', 'n/a')}")
            if s.text:
                cleaned = s.text.replace("<p>", "\n> ").replace("</p>", "")
                lines.append(f"- **Text:** {cleaned[:300]}")
            lines.append("")

        if noise:
            lines.append("## Filtered Out (Noise)\n")
            lines.append("| Title | Score | Reason |")
            lines.append("|-------|-------|--------|")
            for s in noise:
                r = result_map.get(s.id, {})
                lines.append(f"| {s.title} | {s.score} | {r.get('reason', 'n/a')} |")
            lines.append("")
    else:
        for s in stories:
            lines.append(f"### [{s.title}]({s.hn_url})")
            lines.append(
                f"- **Score:** {s.score} | **Comments:** {s.num_comments} | **Author:** @{s.author}"
            )
            if s.url:
                lines.append(f"- **Link:** {s.url}")
            if s.text:
                cleaned = s.text.replace("<p>", "\n> ").replace("</p>", "")
                lines.append(f"- **Text:** {cleaned[:300]}")
            lines.append("")

    return "\n".join(lines)
