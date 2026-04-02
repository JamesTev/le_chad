import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from mistralai.client import Mistral

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 30
MODEL = "mistral-medium-latest"

SYSTEM_PROMPT = """\
You are ChadBot, an AI software engineer that improves codebases based on GitHub issues.

You have tools to explore and modify the repository. Follow this workflow:

1. Start by running `list_files` with directory '.' to see the top-level project layout.
2. Read relevant files with `read_file` to understand the existing code.
3. Use `search_code` to find specific patterns, references, or usages.
4. Plan your changes carefully — make minimal, focused edits that address the issue.
5. Apply changes with `write_file`. Always write the complete file content.

IMPORTANT — Project structure:
- The repo has a workspace member called `le_chad/` which contains a Python package at `le_chad/le_chad/`.
- The actual source files you need to modify are at paths like `le_chad/le_chad/app.py`, `le_chad/le_chad/config.py`, etc.
- All paths passed to tools must be relative to the repo root.
- You may ONLY modify files whose path starts with `le_chad/`. Do NOT write to files outside that directory.
- You can read files anywhere in the repo for context, but all writes must be within `le_chad/`.

Guidelines:
- Understand the codebase before changing anything.
- Maintain existing code style and conventions.
- Do not modify unrelated code.
- When you are done, respond with a clear summary of what you changed and why.\
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the given path (relative to repo root).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file to read",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files in a directory, optionally filtered by a glob pattern. "
                "Excludes .git and .venv directories."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list, relative to repo root (default: '.')",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match (default: '*')",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (relative to repo root). Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search for a string or pattern in files. "
                "Returns matching lines with file paths and line numbers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The string or regex pattern to search for",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File glob to search within (default: '*.py')",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

EXCLUDED_DIRS = {".git", ".venv", "node_modules", "__pycache__"}


class RepoAgent:
    """Runs a Mistral tool-calling loop scoped to a cloned repo directory."""

    def __init__(self, repo_dir: Path) -> None:
        self.repo_dir = repo_dir.resolve()
        self.tool_functions = {
            "read_file": self._read_file,
            "list_files": self._list_files,
            "write_file": self._write_file,
            "search_code": self._search_code,
        }

    def _resolve(self, path: str) -> Path:
        resolved = (self.repo_dir / path).resolve()
        if not str(resolved).startswith(str(self.repo_dir.resolve())):
            raise ValueError(f"Path escapes repo root: {path}")
        return resolved

    def _read_file(self, path: str) -> str:
        try:
            return self._resolve(path).read_text()
        except FileNotFoundError:
            return f"Error: file '{path}' not found"
        except Exception as e:
            return f"Error reading '{path}': {e}"

    def _list_files(self, directory: str = ".", pattern: str = "*") -> str:
        try:
            base = self._resolve(directory)
            files = sorted(
                str(p.relative_to(self.repo_dir))
                for p in base.rglob(pattern)
                if p.is_file() and not (EXCLUDED_DIRS & set(p.parts))
            )
            return "\n".join(files) if files else "No files found"
        except Exception as e:
            return f"Error: {e}"

    def _write_file(self, path: str, content: str) -> str:
        try:
            if not path.startswith("le_chad/"):
                return f"Error: writes are restricted to the le_chad/ directory. Got: '{path}'"
            p = self._resolve(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return f"Successfully wrote '{path}'"
        except Exception as e:
            return f"Error writing '{path}': {e}"

    def _search_code(self, query: str, file_pattern: str = "*.py") -> str:
        try:
            result = subprocess.run(
                ["grep", "-rn", "--include", file_pattern, query, "."],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.repo_dir,
            )
            output = result.stdout.strip()
            return output if output else "No matches found"
        except Exception as e:
            return f"Error: {e}"

    def _execute_tool(self, tool_call) -> str:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        logger.info("Tool call: %s(%s)", name, ", ".join(f"{k}={v!r}" for k, v in args.items()))

        fn = self.tool_functions.get(name)
        if not fn:
            return f"Unknown tool: {name}"
        result = fn(**args)
        logger.info("Tool result (%s): %s", name, result[:500] if len(result) > 500 else result)
        return result

    def run(self, issue_number: int, issue_title: str, issue_body: str) -> str:
        client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"GitHub Issue #{issue_number}: {issue_title}\n\n{issue_body}",
            },
        ]

        summary = ""
        for i in range(MAX_ITERATIONS):
            logger.info("Iteration %d/%d", i + 1, MAX_ITERATIONS)

            response = client.chat.complete(model=MODEL, messages=messages, tools=TOOLS)
            choice = response.choices[0]
            messages.append(choice.message)

            if choice.finish_reason == "stop":
                summary = choice.message.content or ""
                logger.info("Agent finished: %s", summary[:200])
                break

            if choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    result = self._execute_tool(tool_call)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": result,
                        }
                    )
        else:
            logger.warning("Reached max iterations (%d)", MAX_ITERATIONS)
            summary = "Reached maximum iterations. Changes may be incomplete."

        return summary


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def process_issue(repo_full_name: str, issue_number: int, issue_title: str, issue_body: str) -> None:
    """Clone the repo, run the agent, and create a PR with the changes."""
    github_token = os.environ["GITHUB_TOKEN"]
    clone_url = f"https://x-access-token:{github_token}@github.com/{repo_full_name}.git"

    with tempfile.TemporaryDirectory(prefix="chadbot-") as tmpdir:
        repo_dir = Path(tmpdir) / "repo"
        logger.info("Cloning %s into %s", repo_full_name, repo_dir)
        subprocess.run(["git", "clone", clone_url, str(repo_dir)], check=True, capture_output=True)

        # Run the agent
        agent = RepoAgent(repo_dir)
        summary = agent.run(issue_number, issue_title, issue_body)

        # Check if the agent made any changes
        status = _run_git(["status", "--porcelain"], cwd=repo_dir)
        if not status.stdout.strip():
            logger.info("Agent made no changes for issue #%s", issue_number)
            return

        # Create branch, commit, push, and open PR
        branch = f"chadbot/issue-{issue_number}"
        _run_git(["config", "user.name", "ChadBot"], cwd=repo_dir)
        _run_git(["config", "user.email", "chadbot@users.noreply.github.com"], cwd=repo_dir)
        _run_git(["checkout", "-b", branch], cwd=repo_dir)
        _run_git(["add", "-A"], cwd=repo_dir)

        commit_msg = f"fix: address issue #{issue_number} - {issue_title}"
        _run_git(["commit", "-m", commit_msg], cwd=repo_dir)
        _run_git(["push", "-u", "origin", branch], cwd=repo_dir)

        logger.info("Pushed branch %s", branch)

        # Create PR via GitHub API
        pr_body = (
            f"Closes #{issue_number}\n\n"
            f"## Summary\n\n{summary}\n\n"
            f"---\n*Automated by ChadBot*"
        )
        subprocess.run(
            [
                "gh", "pr", "create",
                "--repo", repo_full_name,
                "--title", f"Fix #{issue_number}: {issue_title}",
                "--body", pr_body,
                "--head", branch,
            ],
            cwd=repo_dir,
            check=True,
            env={**os.environ, "GH_TOKEN": github_token},
        )
        logger.info("PR created for issue #%s", issue_number)
