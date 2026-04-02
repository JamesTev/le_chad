"""
Product-aware HN scout: fetches from multiple sources, deduplicates,
runs a two-pass filter (coarse + relevance), and outputs a categorised report.
"""

import asyncio
import re
import time
from pathlib import Path

import httpx

from .hn import (
    HNStory,
    fetch_stories,
    search_stories,
    coarse_filter,
    relevance_filter,
)

DEFAULT_FEEDS = ["show", "top"]
DEFAULT_FEED_LIMIT = 30
DEFAULT_SEARCH_LIMIT = 15
DEFAULT_MIN_SCORE = 5


def load_product_context(context_path: Path) -> str:
    """Load product_context.md and return its contents."""
    path = Path(context_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Product context not found at {path}. "
            "Run `feature-builder context --repo <path>` first."
        )
    return path.read_text()


def extract_keywords(context: str) -> list[str]:
    """Pull search terms from the Discovery Keywords section of the context doc."""
    in_keywords = False
    keywords: list[str] = []
    for line in context.splitlines():
        if re.match(r"^##\s+Discovery Keywords", line, re.IGNORECASE):
            in_keywords = True
            continue
        if in_keywords:
            if line.startswith("## "):
                break
            stripped = line.strip().lstrip("-•*").strip()
            if stripped:
                keywords.append(stripped)
    return keywords


def _deduplicate(stories: list[HNStory]) -> list[HNStory]:
    seen: set[int] = set()
    unique: list[HNStory] = []
    for s in stories:
        if s.id not in seen:
            seen.add(s.id)
            unique.append(s)
    return unique


async def run_scout(
    context_path: Path,
    extra_searches: list[str] | None = None,
    feeds: list[str] | None = None,
    feed_limit: int = DEFAULT_FEED_LIMIT,
    search_limit: int = DEFAULT_SEARCH_LIMIT,
    min_score: int = DEFAULT_MIN_SCORE,
) -> tuple[str, list[HNStory], list[dict]]:
    """Execute the full scout pipeline. Returns (context, stories, relevance_results)."""
    feeds = feeds or DEFAULT_FEEDS

    context = load_product_context(context_path)
    keywords = extract_keywords(context)
    search_terms = keywords[:6]
    if extra_searches:
        search_terms.extend(extra_searches)

    print(f"  Product context loaded ({len(context)} chars)")
    print(f"  Search terms: {search_terms}")
    print(f"  Feeds: {feeds}")

    # --- Fetch from multiple sources in parallel ---
    t0 = time.time()
    async with httpx.AsyncClient(timeout=15) as client:
        feed_tasks = [
            fetch_stories(client, feed, limit=feed_limit, min_score=min_score)
            for feed in feeds
        ]
        search_tasks = [
            search_stories(client, term, limit=search_limit, min_score=min_score)
            for term in search_terms
        ]
        results = await asyncio.gather(*feed_tasks, *search_tasks, return_exceptions=True)

    all_stories: list[HNStory] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            source = feeds[i] if i < len(feeds) else search_terms[i - len(feeds)]
            print(f"  [WARN] Failed to fetch from '{source}': {result}")
            continue
        all_stories.extend(result)

    all_stories = _deduplicate(all_stories)
    print(f"  Fetched {len(all_stories)} unique stories in {time.time() - t0:.1f}s")

    if not all_stories:
        return context, [], []

    # --- Pass 1: coarse filter (idea vs noise) ---
    t0 = time.time()
    coarse_results = await coarse_filter(all_stories)
    coarse_map = {r["id"]: r for r in coarse_results}
    ideas = [s for s in all_stories if coarse_map.get(s.id, {}).get("label") == "idea"]
    print(f"  Pass 1 (coarse): {len(ideas)} ideas from {len(all_stories)} stories in {time.time() - t0:.1f}s")

    if not ideas:
        return context, all_stories, []

    # --- Pass 2: relevance filter against product context ---
    t0 = time.time()
    rel_results = await relevance_filter(ideas, context)
    relevant_count = sum(1 for r in rel_results if r.get("label") == "relevant")
    maybe_count = sum(1 for r in rel_results if r.get("label") == "maybe")
    print(f"  Pass 2 (relevance): {relevant_count} relevant, {maybe_count} maybe in {time.time() - t0:.1f}s")

    return context, ideas, rel_results


def scout_to_markdown(
    stories: list[HNStory],
    relevance_results: list[dict],
    product_name: str = "your product",
) -> str:
    """Render scout results as a categorised markdown report."""
    result_map = {r["id"]: r for r in relevance_results}

    relevant = [(s, result_map[s.id]) for s in stories if result_map.get(s.id, {}).get("label") == "relevant"]
    maybe = [(s, result_map[s.id]) for s in stories if result_map.get(s.id, {}).get("label") == "maybe"]

    relevant.sort(key=lambda x: x[0].score, reverse=True)
    maybe.sort(key=lambda x: x[0].score, reverse=True)

    lines = [f"# Scout Report for {product_name}\n"]
    lines.append(f"**{len(relevant)} relevant** + {len(maybe)} maybe from {len(stories)} ideas scanned\n")

    if relevant:
        categories: dict[str, list[tuple[HNStory, dict]]] = {}
        for s, r in relevant:
            cat = r.get("category", "other")
            categories.setdefault(cat, []).append((s, r))

        lines.append("## Relevant Discoveries\n")
        category_labels = {
            "tool": "Tools",
            "library": "Libraries",
            "mcp": "MCPs & Integrations",
            "technique": "Techniques",
            "product": "Products",
            "other": "Other",
        }
        for cat in ["tool", "library", "mcp", "technique", "product", "other"]:
            items = categories.get(cat, [])
            if not items:
                continue
            lines.append(f"### {category_labels[cat]}\n")
            for s, r in items:
                lines.append(f"- **[{s.title}]({s.hn_url})** ({s.score}pts)")
                if s.url:
                    lines.append(f"  - Link: {s.url}")
                lines.append(f"  - {r.get('reason', 'n/a')}")
            lines.append("")

    if maybe:
        lines.append("## Worth a Look\n")
        for s, r in maybe[:15]:
            reason = r.get("reason", "")
            lines.append(f"- [{s.title}]({s.hn_url}) ({s.score}pts) — {reason}")
        lines.append("")

    return "\n".join(lines)
