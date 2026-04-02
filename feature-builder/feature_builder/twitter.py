"""
Twitter API client for fetching tweets mentioning Le Chad,
plus Claude-powered tweet analysis.
"""

import json
import os
import sys
from dataclasses import dataclass, asdict

import httpx

from .llm import chat_json

BEARER_TOKEN_ENV = "TWITTER_BEARER_TOKEN"
SEARCH_QUERY = "LeChadBot -is:retweet lang:en"

ANALYSIS_SYSTEM_PROMPT = """\
You are a product intelligence analyst for Le Chad. Your job is to analyze tweets
mentioning Le Chad and extract actionable product insights.

For every batch of tweets you receive, you must:

1. Read each tweet carefully, considering context, tone, and intent.
2. Classify each tweet into exactly ONE primary category:
   - **BUG** — The user is reporting something broken, an error, a crash, or unexpected behavior.
   - **FEATURE_REQUEST** — The user is suggesting a new feature, improvement, or enhancement.
   - **COMPLAINT** — The user is expressing dissatisfaction, frustration, or negative sentiment (but not reporting a specific bug).
   - **PRAISE** — The user is expressing positive sentiment or satisfaction.
   - **NEUTRAL** — The tweet mentions Le Chad but has no actionable signal (news, memes, general mentions).

3. For each tweet, extract:
   - `tweet_id`: The tweet's unique ID.
   - `author`: The Twitter handle.
   - `category`: One of the categories above.
   - `severity`: "critical" | "high" | "medium" | "low" (based on user impact and urgency).
   - `summary`: A one-sentence plain-language summary of the issue or suggestion.
   - `keywords`: 2-5 relevant keywords for grouping/search.
   - `requires_response`: true/false — whether the team should respond to this user.

4. After classifying all tweets, provide a `report` section with:
   - `total_analyzed`: Number of tweets processed.
   - `category_counts`: Count per category.
   - `top_issues`: Up to 5 most critical/frequent issues, deduplicated and ranked.
   - `trending_requests`: Up to 3 most-requested features if any pattern emerges.

Respond ONLY with valid JSON. No markdown, no preamble, no explanation."""


@dataclass
class Tweet:
    id: str
    text: str
    author_id: str
    username: str
    created_at: str | None = None


def _get_bearer_token() -> str:
    token = os.environ.get(BEARER_TOKEN_ENV)
    if not token:
        print(f"[ERROR] {BEARER_TOKEN_ENV} not set. Export it or add to .env.")
        sys.exit(1)
    return token


async def fetch_tweets(
    query: str = SEARCH_QUERY,
    max_results: int = 50,
) -> list[Tweet]:
    """Fetch recent tweets matching the query. Tries v2, falls back to v1.1."""
    token = _get_bearer_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15) as client:
        # Try v2 first
        v2_url = "https://api.twitter.com/2/tweets/search/recent"
        v2_params = {
            "query": query,
            "max_results": min(max(max_results, 10), 100),
            "tweet.fields": "author_id,created_at,text",
            "expansions": "author_id",
            "user.fields": "username",
        }
        resp = await client.get(v2_url, headers=headers, params=v2_params)

        if resp.status_code == 200:
            data = resp.json()
            users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}
            return [
                Tweet(
                    id=t["id"],
                    text=t["text"],
                    author_id=t["author_id"],
                    username=users.get(t["author_id"], "unknown"),
                    created_at=t.get("created_at"),
                )
                for t in data.get("data", [])
            ]

        # Fall back to v1.1
        v1_url = "https://api.twitter.com/1.1/search/tweets.json"
        v1_params = {
            "q": query,
            "count": min(max_results, 100),
            "result_type": "recent",
            "tweet_mode": "extended",
        }
        resp = await client.get(v1_url, headers=headers, params=v1_params)
        resp.raise_for_status()
        data = resp.json()

        return [
            Tweet(
                id=str(t["id"]),
                text=t.get("full_text", t.get("text", "")),
                author_id=str(t["user"]["id"]),
                username=t["user"]["screen_name"],
                created_at=t.get("created_at"),
            )
            for t in data.get("statuses", [])
        ]


def analyze_tweets(tweets: list[Tweet]) -> dict:
    """Send tweets to Claude for classification and insight extraction."""
    if not tweets:
        return {"tweets": [], "report": {"total_analyzed": 0}}

    tweets_json = json.dumps(
        [{"tweet_id": t.id, "author": f"@{t.username}", "text": t.text} for t in tweets],
        indent=2,
    )
    user_message = (
        "Analyze the following tweets mentioning Le Chad. "
        "Classify and extract insights as instructed.\n\n"
        f"Tweets:\n{tweets_json}"
    )
    return chat_json(system=ANALYSIS_SYSTEM_PROMPT, user_message=user_message)
