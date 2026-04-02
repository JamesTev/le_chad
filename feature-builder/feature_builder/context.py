"""
Scan a product codebase and generate a semantic product_context.md via Mistral.
"""

import os
from pathlib import Path

from .hn import _get_mistral_client

CONTEXT_SYSTEM_PROMPT = """\
You are a senior product analyst. You will receive the full source code of a software product.

Produce a structured **product context document** in Markdown. This document will be consumed by
an automated scout agent that watches Hacker News for tools, libraries, MCPs, and techniques
relevant to this product. Be concrete and specific — the scout needs actionable keywords.

Use EXACTLY this structure:

# Product Context: <product name>

## One-liner
<single sentence: what the product does and for whom>

## Tech Stack
<bullet list of languages, frameworks, databases, key libraries>

## Domain & User Persona
<1-2 sentences on the domain and who uses this>

## Feature Inventory
<bullet list of what the product does today, grouped by area>

## Architecture Notes
<brief description of how the system is structured: API style, data layer, deployment model>

## Known Gaps & Pain Points
<bullet list of issues, anti-patterns, missing features, and security problems you can infer
from the code — be specific, cite function names or patterns>

## Discovery Keywords
<bullet list of 15-25 concrete search terms the scout should use to find relevant HN posts.
Include: specific library names, tool categories, problem domains, competitor names,
and technology-specific terms. These should be terms someone would actually post on HN.>

Be thorough but concise. Focus on facts derivable from the code, not speculation."""


SUPPORTED_EXTENSIONS = {".py", ".toml", ".md", ".yaml", ".yml", ".json", ".cfg", ".ini", ".txt"}
MAX_FILE_SIZE = 50_000


def gather_repo_files(repo_path: Path) -> dict[str, str]:
    """Read all relevant source files from a repo directory."""
    files: dict[str, str] = {}
    repo_path = repo_path.resolve()

    for root, dirs, filenames in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".venv", ".git", "node_modules", ".egg-info"}]
        for fname in sorted(filenames):
            fpath = Path(root) / fname
            if fpath.suffix not in SUPPORTED_EXTENSIONS:
                continue
            rel = fpath.relative_to(repo_path)
            try:
                content = fpath.read_text(errors="replace")
                if len(content) > MAX_FILE_SIZE:
                    content = content[:MAX_FILE_SIZE] + "\n... (truncated)"
                files[str(rel)] = content
            except OSError:
                continue

    return files


def _format_files_for_prompt(files: dict[str, str]) -> str:
    parts = []
    for rel_path, content in files.items():
        parts.append(f"=== {rel_path} ===\n{content}")
    return "\n\n".join(parts)


async def generate_product_context(repo_path: Path) -> str:
    """Read a repo and ask Mistral to produce a product context document."""
    files = gather_repo_files(repo_path)
    if not files:
        raise ValueError(f"No supported files found in {repo_path}")

    file_listing = ", ".join(files.keys())
    print(f"  Read {len(files)} files: {file_listing}")

    prompt_body = _format_files_for_prompt(files)

    client = _get_mistral_client()
    resp = await client.chat.complete_async(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": CONTEXT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_body},
        ],
        temperature=0.2,
    )

    return resp.choices[0].message.content
