"""
CLI to explore HN stories and filter for product ideas.

Usage:
  uv run feature-builder feed top --limit 20 --min-score 50
  uv run feature-builder feed show --limit 10 --min-score 5 --filter
  uv run feature-builder user shihn --limit 10 --min-score 100
  uv run feature-builder user shihn fogleman mholt --min-score 50 --filter
  uv run feature-builder search "Show HN" --limit 15 --min-score 100 --filter
  uv run feature-builder search "AI agent" --min-score 20 --filter --output ideas.md
  uv run feature-builder context --repo ./le_chad
  uv run feature-builder scout --context product_context.md --output discoveries.md
"""

import argparse
import asyncio
import time
from pathlib import Path

from dotenv import load_dotenv
import httpx

from .hn import (
    HNStory,
    fetch_stories,
    fetch_user_stories,
    search_stories,
    coarse_filter,
    stories_to_markdown,
)
from .context import generate_product_context
from .scout import run_scout, scout_to_markdown

load_dotenv()


def print_stories(stories: list[HNStory], show_text: bool = False) -> None:
    for i, s in enumerate(stories, 1):
        print(f"  {i:>3}. [{s.score:>4}pts | {s.num_comments:>3}c] {s.title}")
        print(f"       @{s.author} | {s.hn_url}")
        if s.url:
            print(f"       {s.url}")
        if show_text and s.text:
            cleaned = s.text.replace("<p>", " ").replace("</p>", "")[:200]
            print(f"       > {cleaned}")


def print_filtered(
    stories: list[HNStory], results: list[dict], show_noise: bool = False
) -> None:
    result_map = {r["id"]: r for r in results}
    ideas = [s for s in stories if result_map.get(s.id, {}).get("label") == "idea"]
    noise = [s for s in stories if result_map.get(s.id, {}).get("label") == "noise"]

    print(f"\n  IDEAS ({len(ideas)}):")
    for i, s in enumerate(ideas, 1):
        reason = result_map.get(s.id, {}).get("reason", "")
        print(f"  {i:>3}. [{s.score:>4}pts] {s.title}")
        print(f"       {reason} | @{s.author} | {s.hn_url}")

    if show_noise and noise:
        print(f"\n  NOISE ({len(noise)}):")
        for s in noise[:10]:
            reason = result_map.get(s.id, {}).get("reason", "")
            print(f"       [{s.score:>4}pts] {s.title} — {reason}")


async def cmd_feed(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        t0 = time.time()
        stories = await fetch_stories(
            client, args.feed_name, limit=args.limit, min_score=args.min_score
        )
        print(f"\n  Fetched {len(stories)} stories from /{args.feed_name} (>= {args.min_score}pts) in {time.time() - t0:.1f}s")

        if args.filter:
            t0 = time.time()
            results = await coarse_filter(stories)
            print(f"  Filtered in {time.time() - t0:.1f}s")
            print_filtered(stories, results, show_noise=args.verbose)
            if args.output:
                md = stories_to_markdown(stories, results, title=f"HN /{args.feed_name} Ideas")
                with open(args.output, "w") as f:
                    f.write(md)
                print(f"\n  Saved to {args.output}")
        else:
            print_stories(stories, show_text=args.verbose)
            if args.output:
                md = stories_to_markdown(stories, title=f"HN /{args.feed_name} Stories")
                with open(args.output, "w") as f:
                    f.write(md)
                print(f"\n  Saved to {args.output}")


async def cmd_user(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        all_stories: list[HNStory] = []
        for username in args.usernames:
            t0 = time.time()
            stories = await fetch_user_stories(
                client, username, limit=args.limit, min_score=args.min_score
            )
            print(f"\n  @{username}: {len(stories)} stories (>= {args.min_score}pts) in {time.time() - t0:.1f}s")
            if not args.filter:
                print_stories(stories, show_text=args.verbose)
            all_stories.extend(stories)

        if args.filter and all_stories:
            t0 = time.time()
            results = await coarse_filter(all_stories)
            print(f"\n  Filtered {len(all_stories)} stories in {time.time() - t0:.1f}s")
            print_filtered(all_stories, results, show_noise=args.verbose)
            if args.output:
                users_str = ", ".join(f"@{u}" for u in args.usernames)
                md = stories_to_markdown(all_stories, results, title=f"Ideas from {users_str}")
                with open(args.output, "w") as f:
                    f.write(md)
                print(f"\n  Saved to {args.output}")
        elif args.output and not args.filter:
            users_str = ", ".join(f"@{u}" for u in args.usernames)
            md = stories_to_markdown(all_stories, title=f"Stories from {users_str}")
            with open(args.output, "w") as f:
                f.write(md)
            print(f"\n  Saved to {args.output}")


async def cmd_search(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        t0 = time.time()
        stories = await search_stories(
            client, args.query, limit=args.limit, min_score=args.min_score
        )
        print(f"\n  Found {len(stories)} results for '{args.query}' (>= {args.min_score}pts) in {time.time() - t0:.1f}s")

        if args.filter:
            t0 = time.time()
            results = await coarse_filter(stories)
            print(f"  Filtered in {time.time() - t0:.1f}s")
            print_filtered(stories, results, show_noise=args.verbose)
            if args.output:
                md = stories_to_markdown(stories, results, title=f"Ideas — search: '{args.query}'")
                with open(args.output, "w") as f:
                    f.write(md)
                print(f"\n  Saved to {args.output}")
        else:
            print_stories(stories, show_text=args.verbose)
            if args.output:
                md = stories_to_markdown(stories, title=f"Search: '{args.query}'")
                with open(args.output, "w") as f:
                    f.write(md)
                print(f"\n  Saved to {args.output}")


async def cmd_context(args: argparse.Namespace) -> None:
    repo_path = Path(args.repo).resolve()
    output_path = Path(args.output)
    print(f"\n  Scanning {repo_path} ...")

    md = await generate_product_context(repo_path)
    output_path.write_text(md)
    print(f"  Product context written to {output_path} ({len(md)} chars)")


async def cmd_scout(args: argparse.Namespace) -> None:
    context_path = Path(args.context)
    extra = args.also_search or []

    print(f"\n  Starting scout (context: {context_path})")

    _context, ideas, rel_results = await run_scout(
        context_path=context_path,
        extra_searches=extra,
        min_score=args.min_score,
    )

    if not rel_results:
        print("  No relevant discoveries found.")
        return

    product_name = "le Chad"
    for line in _context.splitlines():
        if line.startswith("# Product Context:"):
            product_name = line.split(":", 1)[1].strip()
            break

    md = scout_to_markdown(ideas, rel_results, product_name=product_name)

    if args.output:
        Path(args.output).write_text(md)
        print(f"\n  Report saved to {args.output}")
    else:
        print("\n" + md)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Explore Hacker News and filter for product ideas using Mistral"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--limit", "-n", type=int, default=20, help="Max stories to fetch")
        p.add_argument("--min-score", "-s", type=int, default=0, help="Minimum upvote score")
        p.add_argument("--filter", "-f", action="store_true", help="Run Mistral idea filter")
        p.add_argument("--output", "-o", type=str, help="Output results to .md file")
        p.add_argument("--verbose", "-v", action="store_true", help="Show extra detail (text, noise)")

    feed_p = sub.add_parser("feed", help="Fetch from a HN feed (top/show/new/best/ask)")
    feed_p.add_argument("feed_name", choices=["top", "show", "new", "best", "ask"])
    add_common(feed_p)

    user_p = sub.add_parser("user", help="Fetch stories by user handle(s)")
    user_p.add_argument("usernames", nargs="+", help="HN username(s)")
    add_common(user_p)

    search_p = sub.add_parser("search", help="Full-text search across HN")
    search_p.add_argument("query", help="Search query")
    add_common(search_p)

    ctx_p = sub.add_parser("context", help="Generate product_context.md from a codebase")
    ctx_p.add_argument("--repo", "-r", required=True, help="Path to the product repo")
    ctx_p.add_argument("--output", "-o", default="product_context.md", help="Output file path")

    scout_p = sub.add_parser("scout", help="Scout HN for tools/libraries relevant to your product")
    scout_p.add_argument("--context", "-c", default="product_context.md", help="Path to product_context.md")
    scout_p.add_argument("--output", "-o", type=str, help="Output report to .md file")
    scout_p.add_argument("--min-score", "-s", type=int, default=5, help="Minimum upvote score")
    scout_p.add_argument("--also-search", nargs="*", help="Extra HN search terms")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "feed": cmd_feed,
        "user": cmd_user,
        "search": cmd_search,
        "context": cmd_context,
        "scout": cmd_scout,
    }
    asyncio.run(handlers[args.command](args))


if __name__ == "__main__":
    main()
