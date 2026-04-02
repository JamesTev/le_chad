import hashlib
import hmac
import logging
import os
import subprocess
import threading

from agent.guardrail import check_issue_content
from agent.improve import process_issue

logger = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the GitHub webhook signature (X-Hub-Signature-256)."""
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_issue_opened(payload: dict) -> None:
    """Handle a newly opened GitHub issue by running the agent in the background."""
    issue = payload["issue"]
    repo = payload["repository"]["full_name"]
    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_body = issue.get("body") or ""

    logger.info(
        "New issue #%s opened in %s: %s",
        issue_number,
        repo,
        issue_title,
    )

    thread = threading.Thread(
        target=_run_agent_safe,
        args=(repo, issue_number, issue_title, issue_body),
        daemon=True,
    )
    thread.start()


def _comment_on_issue(repo: str, issue_number: int, body: str) -> None:
    github_token = os.environ.get("GITHUB_TOKEN", "")
    try:
        subprocess.run(
            [
                "gh", "issue", "comment",
                str(issue_number),
                "--repo", repo,
                "--body", body,
            ],
            check=True,
            capture_output=True,
            env={**os.environ, "GH_TOKEN": github_token},
        )
        logger.info("Commented on issue #%s in %s", issue_number, repo)
    except Exception:
        logger.exception("Failed to comment on issue #%s in %s", issue_number, repo)


def _run_agent_safe(repo: str, issue_number: int, issue_title: str, issue_body: str) -> None:
    try:
        flagged_policies = check_issue_content(issue_number, issue_title, issue_body)
        if flagged_policies:
            logger.warning(
                "Issue #%s in %s blocked by guardrail, skipping agent",
                issue_number,
                repo,
            )
            policies_list = "\n".join(f"- {p}" for p in flagged_policies)
            comment = (
                "This issue has been flagged by our content guardrail "
                "(powered by [White Circle](https://whitecircle.ai)) "
                "and will not be processed automatically.\n\n"
                f"**Violated policies:**\n{policies_list}\n\n"
                "Please review the issue content and resubmit if appropriate.\n\n"
                "---\n*ChadBot Safety Check*"
            )
            _comment_on_issue(repo, issue_number, comment)
            return

        logger.info("Starting agent for issue #%s in %s", issue_number, repo)
        process_issue(repo, issue_number, issue_title, issue_body)
        logger.info("Agent completed for issue #%s in %s", issue_number, repo)
    except Exception:
        logger.exception("Agent failed for issue #%s in %s", issue_number, repo)
