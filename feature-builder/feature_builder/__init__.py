"""feature-builder: HN-powered product idea discovery agent."""

from .hn import (
    HNStory,
    coarse_filter,
    fetch_stories,
    fetch_user_stories,
    relevance_filter,
    search_stories,
    stories_to_markdown,
)
from .context import generate_product_context
from .scout import run_scout, scout_to_markdown

__all__ = [
    "HNStory",
    "coarse_filter",
    "fetch_stories",
    "fetch_user_stories",
    "generate_product_context",
    "relevance_filter",
    "run_scout",
    "scout_to_markdown",
    "search_stories",
    "stories_to_markdown",
]
