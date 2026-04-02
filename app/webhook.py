import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the GitHub webhook signature (X-Hub-Signature-256)."""
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_issue_opened(payload: dict) -> None:
    """Handle a newly opened GitHub issue."""
    issue = payload["issue"]
    repo = payload["repository"]["full_name"]
    logger.info(
        "New issue #%s opened in %s: %s",
        issue["number"],
        repo,
        issue["title"],
    )
    logger.info("Author: %s", issue["user"]["login"])
    if issue.get("body"):
        logger.info("Body: %s", issue["body"][:200])
