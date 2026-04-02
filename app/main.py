import json
import logging
import os
from dataclasses import asdict
from urllib.parse import parse_qs

from dotenv import load_dotenv

load_dotenv()

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.webhook import handle_issue_opened, verify_signature
from feature_builder.hn import fetch_stories, search_stories, coarse_filter
from feature_builder.twitter import fetch_tweets, analyze_tweets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Webhook Listener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
) -> dict:
    body = await request.body()

    if WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature")
        if not verify_signature(body, x_hub_signature_256, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

    if not body or not body.strip():
        logger.info("Received event: %s (empty body)", x_github_event)
        return {"status": "ok"}

    content_type = request.headers.get("content-type", "")
    logger.info("Content-Type: %s", content_type)

    try:
        if "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(body.decode())
            payload = json.loads(parsed["payload"][0])
        else:
            payload = json.loads(body)
    except (json.JSONDecodeError, KeyError):
        logger.warning("Could not parse body for event: %s, body: %s", x_github_event, body[:200])
        return {"status": "ok"}

    logger.info("Received event: %s (action: %s)", x_github_event, payload.get("action"))

    if x_github_event == "issues" and payload.get("action") == "opened":
        handle_issue_opened(payload)

    return {"status": "ok"}


# ── Category / severity mapping helpers ─────────────────────────────────────

CATEGORY_MAP = {
    "BUG": "Bug",
    "FEATURE_REQUEST": "Feature Request",
    "COMPLAINT": "Complaint",
    "PRAISE": "Praise",
    "NEUTRAL": "Praise",
    "idea": "Feature Request",
    "noise": "Neutral",
}

SEVERITY_MAP = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def _hn_to_issues(stories, filter_results=None):
    """Convert HN stories + optional Mistral filter results into frontend issue format."""
    result_map = {r["id"]: r for r in (filter_results or [])}
    issues = []
    for s in stories:
        fr = result_map.get(s.id, {})
        label = fr.get("label", "idea")
        category = CATEGORY_MAP.get(label, "Feature Request")
        issues.append({
            "id": s.id,
            "title": s.title,
            "category": category,
            "severity": "Medium" if s.score < 100 else "High" if s.score < 500 else "Critical",
            "sourceDetail": f"HN #{s.id}",
            "timeAgo": f"{s.score} pts",
            "url": s.hn_url,
        })
    return issues


def _tweets_to_issues(tweets, analysis):
    """Convert tweet analysis results into frontend issue format."""
    analyzed = {str(t.get("tweet_id", "")): t for t in analysis.get("tweets", [])}
    issues = []
    for tw in tweets:
        info = analyzed.get(tw.id, {})
        category = CATEGORY_MAP.get(info.get("category", "NEUTRAL"), "Praise")
        severity = SEVERITY_MAP.get(info.get("severity", "low"), "Low")
        issues.append({
            "id": tw.id,
            "title": info.get("summary", tw.text[:120]),
            "category": category,
            "severity": severity,
            "sourceDetail": f"@{tw.username}",
            "timeAgo": tw.created_at or "recently",
            "url": f"https://x.com/{tw.username}/status/{tw.id}",
        })
    return issues


# ── Scan endpoint ───────────────────────────────────────────────────────────

@app.post("/api/scan")
async def scan():
    """Run a scan across HN and Twitter, returning categorised issues."""
    results = {"hackernews": [], "twitter": [], "github": []}
    errors = []

    # --- Hacker News ---
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            stories = await search_stories(client, query="chatbot OR AI agent OR LLM", limit=15)
        try:
            filter_results = await coarse_filter(stories)
        except (Exception, SystemExit):
            logger.warning("Mistral filter failed, returning unfiltered HN stories")
            filter_results = None
        results["hackernews"] = _hn_to_issues(stories, filter_results)
    except (Exception, SystemExit) as exc:
        logger.exception("HN scan failed")
        errors.append(f"hackernews: {exc}")

    # --- Twitter ---
    try:
        tweets = await fetch_tweets(max_results=20)
        try:
            analysis = analyze_tweets(tweets)
        except (Exception, SystemExit):
            logger.warning("Tweet analysis failed (missing ANTHROPIC_API_KEY?), returning raw tweets")
            analysis = {"tweets": []}
        results["twitter"] = _tweets_to_issues(tweets, analysis)
    except (Exception, SystemExit) as exc:
        logger.exception("Twitter scan failed")
        errors.append(f"twitter: {exc}")

    # --- GitHub (placeholder — already handled by webhook) ---
    # GitHub issues arrive via webhook, not polling. This column stays empty
    # unless you add a REST scan here later.

    return {"results": results, "errors": errors}
