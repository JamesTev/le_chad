"""
FastAPI server exposing the scout pipeline as a JSON API for the dashboard.

Start with:  uv run uvicorn feature_builder.api:app --port 8001 --reload
"""

from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .hn import HNStory
from .scout import run_scout, load_product_context, extract_keywords
from .pipeline import run_pipeline
from .logger import read_logs

load_dotenv()

app = FastAPI(title="Feature Builder API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_CONTEXT_PATH = Path("product_context.md")


def _story_to_dict(story: HNStory) -> dict:
    d = asdict(story)
    d["hn_url"] = story.hn_url
    return d


def _build_discovery(story: HNStory, rel: dict) -> dict:
    return {
        **_story_to_dict(story),
        "label": rel.get("label", "noise"),
        "category": rel.get("category", "other"),
        "reason": rel.get("reason", ""),
    }


@app.get("/api/scout/context")
async def get_context():
    if not DEFAULT_CONTEXT_PATH.exists():
        raise HTTPException(404, "product_context.md not found. Run: feature-builder context --repo ./le_chad")
    raw = DEFAULT_CONTEXT_PATH.read_text()
    keywords = extract_keywords(raw)
    return {"context": raw, "keywords": keywords}


@app.post("/api/scout/run")
async def run_scout_endpoint():
    if not DEFAULT_CONTEXT_PATH.exists():
        raise HTTPException(404, "product_context.md not found")

    context, ideas, rel_results = await run_scout(
        context_path=DEFAULT_CONTEXT_PATH,
        min_score=5,
    )

    result_map = {r["id"]: r for r in rel_results}
    discoveries = []
    for story in ideas:
        rel = result_map.get(story.id)
        if rel and rel.get("label") in ("relevant", "maybe"):
            discoveries.append(_build_discovery(story, rel))

    discoveries.sort(key=lambda d: (0 if d["label"] == "relevant" else 1, -d["score"]))

    product_name = "le Chad"
    for line in context.splitlines():
        if line.startswith("# Product Context:"):
            product_name = line.split(":", 1)[1].strip()
            break

    return {
        "product_name": product_name,
        "total_fetched": len(ideas),
        "relevant_count": sum(1 for d in discoveries if d["label"] == "relevant"),
        "maybe_count": sum(1 for d in discoveries if d["label"] == "maybe"),
        "discoveries": discoveries,
    }


DEFAULT_REPO_PATH = Path("le_chad")
DEFAULT_LOG_PATH = Path("pipeline_runs.jsonl")


@app.post("/api/pipeline/run")
async def run_pipeline_endpoint(max_ideas: int = 1, dry_run: bool = False):
    if not DEFAULT_CONTEXT_PATH.exists():
        raise HTTPException(404, "product_context.md not found")
    repo = DEFAULT_REPO_PATH.resolve()
    if not repo.exists():
        raise HTTPException(404, f"Target repo not found at {repo}")

    logs = await run_pipeline(
        context_path=DEFAULT_CONTEXT_PATH,
        repo_path=repo,
        log_path=DEFAULT_LOG_PATH,
        max_ideas=max_ideas,
        dry_run=dry_run,
    )
    return {"runs": logs}


@app.get("/api/pipeline/logs")
async def get_pipeline_logs(last: int = 20):
    entries = read_logs(DEFAULT_LOG_PATH)
    return {"logs": entries[-last:]}
