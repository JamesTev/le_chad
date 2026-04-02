import logging
import os

import httpx

logger = logging.getLogger(__name__)

WHITECIRCLE_API_URL = "https://eu.whitecircle.ai/api/session/check"
WHITECIRCLE_API_VERSION = "2025-12-01"


def check_issue_content(
    issue_number: int, issue_title: str, issue_body: str
) -> list[str]:
    """Check issue title and body for policy violations via WhiteCircle.

    Returns an empty list if the content is safe, or a list of flagged policy names.
    """
    api_key = os.environ.get("WHITECIRCLE_API_KEY")
    deployment_id = os.environ.get("WHITECIRCLE_DEPLOYMENT_ID")

    if not api_key or not deployment_id:
        logger.warning("WhiteCircle credentials not set, skipping guardrail check")
        return []

    content = f"{issue_title}\n\n{issue_body}"

    payload = {
        "deployment_id": deployment_id,
        "external_session_id": f"github-issue-{issue_number}",
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }

    try:
        response = httpx.post(
            WHITECIRCLE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "whitecircle-version": WHITECIRCLE_API_VERSION,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("flagged"):
            flagged_policies = [
                info["name"]
                for info in result.get("policies", {}).values()
                if info.get("flagged")
            ]
            logger.warning(
                "Issue #%s flagged by WhiteCircle: %s",
                issue_number,
                ", ".join(flagged_policies),
            )
            return flagged_policies

        logger.info("Issue #%s passed WhiteCircle guardrail check", issue_number)
        return []

    except Exception:
        logger.exception("WhiteCircle guardrail check failed for issue #%s", issue_number)
        return []
