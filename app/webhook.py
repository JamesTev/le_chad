import hashlib
import hmac
import logging
import threading

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


def _run_agent_safe(repo: str, issue_number: int, issue_title: str, issue_body: str) -> None:
    try:
        logger.info("Starting agent for issue #%s in %s", issue_number, repo)
        process_issue(repo, issue_number, issue_title, issue_body)
        logger.info("Agent completed for issue #%s in %s", issue_number, repo)
    except Exception:
        logger.exception("Agent failed for issue #%s in %s", issue_number, repo)
