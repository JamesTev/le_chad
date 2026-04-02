"""
Feasibility test: fetch HN stories, filter by score + Mistral, output to .md
"""

import asyncio
import time

from dotenv import load_dotenv
import httpx

from feature_builder.hn import (
    fetch_stories,
    fetch_user_stories,
    coarse_filter,
    stories_to_markdown,
)

load_dotenv()

OUTPUT_FILE = "feasibility_output.md"


async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        # --- Test 1: Fetch from feeds with min_score filter ---
        print("=" * 60)
        print("TEST 1: Fetch stories (min_score=5)")
        print("=" * 60)

        for feed in ["top", "show"]:
            t0 = time.time()
            stories = await fetch_stories(client, feed, limit=15, min_score=5)
            elapsed = time.time() - t0
            print(
                f"\n  [{feed.upper()}] {len(stories)} stories (>= 5pts) in {elapsed:.1f}s"
            )
            for s in stories[:3]:
                print(f"    - [{s.score}pts] {s.title}")

        # --- Test 2: Fetch by user handle with min_score ---
        print("\n" + "=" * 60)
        print("TEST 2: User stories (min_score=50)")
        print("=" * 60)

        test_users = ["shihn", "fogleman", "mholt"]
        for username in test_users:
            t0 = time.time()
            stories = await fetch_user_stories(client, username, limit=5, min_score=50)
            elapsed = time.time() - t0
            print(
                f"\n  [@{username}] {len(stories)} stories (>= 50pts) in {elapsed:.1f}s"
            )
            for s in stories:
                print(f"    - [{s.score}pts] {s.title}")

        # --- Test 3: Coarse filter + markdown output ---
        print("\n" + "=" * 60)
        print("TEST 3: Coarse-filter & output to markdown")
        print("=" * 60)

        top = await fetch_stories(client, "top", limit=25, min_score=10)
        show = await fetch_stories(client, "show", limit=15, min_score=3)
        all_stories = top + show
        print(f"\n  Collected {len(all_stories)} stories (top>=10pts, show>=3pts)")

        t0 = time.time()
        results = await coarse_filter(all_stories)
        elapsed = time.time() - t0

        ideas = [r for r in results if r.get("label") == "idea"]
        noise = [r for r in results if r.get("label") == "noise"]
        print(
            f"  Mistral filter: {len(ideas)} ideas, {len(noise)} noise in {elapsed:.1f}s"
        )

        md = stories_to_markdown(
            all_stories, results, title="Feasibility Test — HN Product Ideas"
        )
        with open(OUTPUT_FILE, "w") as f:
            f.write(md)
        print(f"\n  Output written to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
