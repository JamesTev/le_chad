"""
Thin wrapper around the Mistral SDK for LLM calls.
"""

import json
import os
import sys

from mistralai.client import Mistral


def _get_client() -> Mistral:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("[ERROR] MISTRAL_API_KEY not set. Create a .env file or export it.")
        sys.exit(1)
    return Mistral(api_key=api_key)


def chat_json(
    system: str,
    user_message: str,
    model: str = "mistral-small-latest",
    max_tokens: int = 4096,
) -> dict:
    """Send a system+user message to Mistral and parse the response as JSON."""
    client = _get_client()
    resp = client.chat.complete(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"[WARN] Failed to parse LLM response:\n{raw[:500]}")
        return {}
