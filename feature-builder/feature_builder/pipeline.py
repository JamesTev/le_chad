"""
End-to-end feature builder pipeline.

Scout HN -> filter ideas -> plan -> implement -> test -> PR -> log
"""

import time
from pathlib import Path

from .hn import HNStory
from .scout import run_scout
from .planner import generate_plan
from .implementer import apply_changes, run_test
from .git_ops import (
    create_branch,
    commit_changes,
    push_branch,
    create_pr,
    checkout_main,
)
from .logger import log_run


async def run_pipeline(
    context_path: Path,
    repo_path: Path,
    log_path: Path | None = None,
    max_ideas: int = 3,
    min_score: int = 5,
    dry_run: bool = False,
) -> list[dict]:
    """
    Run the full feature-builder pipeline:
    1. Scout HN for relevant ideas
    2. For each top idea: plan -> implement -> test -> PR
    3. Log results

    Returns list of log entries (one per idea attempted).
    """
    print("=" * 60)
    print("FEATURE BUILDER PIPELINE")
    print("=" * 60)

    # --- Stage 1: Scout ---
    print("\n[1/5] Scouting HN for ideas...")
    context, ideas, rel_results = await run_scout(
        context_path=context_path,
        min_score=min_score,
    )

    if not rel_results:
        print("  No relevant ideas found. Pipeline done.")
        return []

    result_map = {r["id"]: r for r in rel_results}
    relevant = [
        (s, result_map[s.id])
        for s in ideas
        if result_map.get(s.id, {}).get("label") in ("relevant", "maybe")
    ]
    relevant.sort(key=lambda x: (0 if x[1]["label"] == "relevant" else 1, -x[0].score))
    top_ideas = relevant[:max_ideas]

    print(f"  Top {len(top_ideas)} ideas selected for planning")

    logs = []
    for i, (story, rel_info) in enumerate(top_ideas):
        t0 = time.time()
        print(f"\n{'=' * 60}")
        print(f"IDEA {i + 1}/{len(top_ideas)}: {story.title}")
        print(f"  {story.hn_url} ({story.score}pts)")
        print(f"{'=' * 60}")

        try:
            log_entry = await _process_idea(
                story=story,
                rel_info=rel_info,
                product_context=context,
                repo_path=repo_path,
                log_path=log_path,
                dry_run=dry_run,
                t0=t0,
            )
        except Exception as e:
            print(f"  [ERROR] {e}")
            log_entry = log_run(
                log_path,
                story_id=story.id,
                story_title=story.title,
                hn_url=story.hn_url,
                outcome="error",
                error=str(e),
                duration_s=time.time() - t0,
            )

        logs.append(log_entry)

    print(f"\n{'=' * 60}")
    print("PIPELINE COMPLETE")
    outcomes = [l["outcome"] for l in logs]
    print(f"  {len(logs)} ideas processed: {outcomes}")
    print(f"{'=' * 60}")

    return logs


async def _process_idea(
    story: HNStory,
    rel_info: dict,
    product_context: str,
    repo_path: Path,
    log_path: Path | None,
    dry_run: bool,
    t0: float,
) -> dict:
    """Process a single idea through plan -> implement -> test -> PR."""

    # --- Stage 2: Plan ---
    print("\n[2/5] Generating implementation plan...")
    plan = generate_plan(story, rel_info, product_context)
    print(f"  Plan: {plan.get('title', '?')}")
    print(f"  Summary: {plan.get('summary', '?')}")
    print(f"  Changes: {len(plan.get('changes', []))} files")
    print(f"  Risk: {plan.get('risk', '?')}")

    if not plan.get("changes"):
        print("  No changes planned. Skipping.")
        return log_run(
            log_path,
            story_id=story.id,
            story_title=story.title,
            hn_url=story.hn_url,
            plan_title=plan.get("title", ""),
            plan_summary=plan.get("summary", ""),
            outcome="no_changes",
            duration_s=time.time() - t0,
        )

    if dry_run:
        print("  [DRY RUN] Skipping implementation.")
        return log_run(
            log_path,
            story_id=story.id,
            story_title=story.title,
            hn_url=story.hn_url,
            plan_title=plan.get("title", ""),
            plan_summary=plan.get("summary", ""),
            changes=plan.get("changes", []),
            outcome="dry_run",
            duration_s=time.time() - t0,
        )

    # --- Stage 3: Implement ---
    print("\n[3/5] Implementing changes...")
    branch_name = create_branch(plan, repo_path)
    print(f"  Branch: {branch_name}")

    apply_results = apply_changes(plan, repo_path)
    for ar in apply_results:
        status = ar["status"]
        icon = (
            "OK" if status == "applied" else "SKIP" if status == "skipped" else "FAIL"
        )
        print(
            f"  [{icon}] {ar['file']}: {ar.get('changes_made') or ar.get('reason', '')}"
        )

    applied_count = sum(1 for r in apply_results if r["status"] == "applied")
    if applied_count == 0:
        print("  No changes applied. Returning to main.")
        checkout_main(repo_path)
        return log_run(
            log_path,
            story_id=story.id,
            story_title=story.title,
            hn_url=story.hn_url,
            plan_title=plan.get("title", ""),
            plan_summary=plan.get("summary", ""),
            changes=plan.get("changes", []),
            apply_results=apply_results,
            outcome="no_changes_applied",
            duration_s=time.time() - t0,
        )

    # --- Stage 4: Test ---
    print("\n[4/5] Running tests...")
    test_cmd = plan.get("test_command", "")
    test_result = run_test(test_cmd, repo_path)
    print(f"  Test: {test_result['status']}")
    if test_result.get("stdout"):
        for line in test_result["stdout"].splitlines()[:5]:
            print(f"    {line}")

    # --- Stage 5: PR ---
    pr_result = {"status": "skipped"}
    if test_result["status"] in ("passed", "skipped"):
        print("\n[5/5] Creating PR...")
        committed = commit_changes(plan, repo_path)
        if committed:
            pushed = push_branch(branch_name, repo_path)
            if pushed:
                pr_result = create_pr(plan, branch_name, repo_path)
                print(f"  PR: {pr_result.get('url') or pr_result.get('reason', '?')}")
            else:
                pr_result = {"status": "push_failed"}
                print("  Push failed.")
        else:
            pr_result = {"status": "nothing_to_commit"}
            print("  Nothing to commit.")
    else:
        print("\n[5/5] Test failed — skipping PR.")
        pr_result = {"status": "skipped_test_failed"}

    # Always return to main
    checkout_main(repo_path)

    outcome = "pr_created" if pr_result.get("status") == "created" else "attempted"
    return log_run(
        log_path,
        story_id=story.id,
        story_title=story.title,
        hn_url=story.hn_url,
        plan_title=plan.get("title", ""),
        plan_summary=plan.get("summary", ""),
        changes=plan.get("changes", []),
        apply_results=apply_results,
        test_result=test_result,
        pr_result=pr_result,
        outcome=outcome,
        duration_s=time.time() - t0,
    )
