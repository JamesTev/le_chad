import json
import logging
import os
from urllib.parse import parse_qs

from fastapi import FastAPI, Header, HTTPException, Request

from app.webhook import handle_issue_opened, verify_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Webhook Listener")

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
) -> dict:
    body = await request.body()

    if WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing signature")
        if not verify_signature(body, x_hub_signature_256, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

    if not body or not body.strip():
        logger.info("Received event: %s (empty body)", x_github_event)
        return {"status": "ok"}

    content_type = request.headers.get("content-type", "")
    logger.info("Content-Type: %s", content_type)

    try:
        if "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(body.decode())
            payload = json.loads(parsed["payload"][0])
        else:
            payload = json.loads(body)
    except (json.JSONDecodeError, KeyError):
        logger.warning("Could not parse body for event: %s, body: %s", x_github_event, body[:200])
        return {"status": "ok"}

    logger.info("Received event: %s (action: %s)", x_github_event, payload.get("action"))

    if x_github_event == "issues" and payload.get("action") == "opened":
        handle_issue_opened(payload)

    return {"status": "ok"}
