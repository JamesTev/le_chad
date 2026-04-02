"""
Stage 4: Generate code changes based on a plan, apply them, and test.
"""

import subprocess
from pathlib import Path

from .llm import chat_json

IMPLEMENT_SYSTEM_PROMPT = """\
You are a senior software engineer. You receive:
1. The CURRENT CONTENTS of a file.
2. A PLAN describing what to change.

Your job: produce the complete new file contents with the change applied.

Rules:
- Return the FULL file contents, not a diff or patch.
- Make minimal changes — only what the plan describes.
- Do not add explanatory comments about your changes.
- Preserve existing code style, indentation, and patterns.
- If the plan says to create a new file, produce the full file from scratch.

Respond with a JSON object:
{
  "file_content": "<the complete new file contents as a string>",
  "changes_made": "<1-2 sentence summary of what you changed>"
}"""


def implement_change(
    file_path: Path,
    change_description: str,
    action: str = "modify",
) -> dict:
    """Generate new file contents for a single planned change."""
    if action == "modify" and file_path.exists():
        current_content = file_path.read_text()
        user_msg = (
            f"## CURRENT FILE: {file_path}\n\n"
            f"```\n{current_content}\n```\n\n"
            f"## PLAN\n\n{change_description}"
        )
    else:
        user_msg = (
            f"## NEW FILE: {file_path}\n\n"
            f"## PLAN\n\n{change_description}"
        )

    return chat_json(IMPLEMENT_SYSTEM_PROMPT, user_msg, max_tokens=8192)


def apply_changes(plan: dict, repo_path: Path) -> list[dict]:
    """Apply all changes from a plan to the repo. Returns list of results per file."""
    results = []
    for change in plan.get("changes", []):
        file_rel = change["file"]
        file_path = repo_path / file_rel
        action = change.get("action", "modify")
        description = change["description"]

        try:
            result = implement_change(file_path, description, action)
            content = result.get("file_content", "")
            if not content:
                results.append({
                    "file": file_rel,
                    "status": "skipped",
                    "reason": "LLM returned empty content",
                })
                continue

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            results.append({
                "file": file_rel,
                "status": "applied",
                "changes_made": result.get("changes_made", ""),
            })
        except Exception as e:
            results.append({
                "file": file_rel,
                "status": "failed",
                "reason": str(e),
            })

    return results


def run_test(test_command: str, repo_path: Path, timeout: int = 30) -> dict:
    """Run the plan's test command and return the result."""
    if not test_command:
        return {"status": "skipped", "reason": "no test command provided"}

    try:
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "reason": f"exceeded {timeout}s"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}
