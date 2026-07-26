from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("lark-webhook")

app = FastAPI(
    title="LinkedIn Daily Scanner API",
    description="Railway backend for Lark integration.",
    version="0.2.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "linkedin-daily-scanner-api",
        "status": "running",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/webhooks/lark/events")
async def receive_lark_event(request: Request) -> JSONResponse:
    """Receive Lark URL verification and message events.

    This step intentionally does not trigger LinkedIn scraping or write to
    Supabase. It only verifies that Lark can reach Railway and logs the
    received message identifiers/content for the next implementation step.
    """
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        logger.exception("Invalid JSON received from Lark")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Request body must be valid JSON"},
        )

    logger.info(
        "Lark payload received:\n%s",
        json.dumps(payload, ensure_ascii=False, indent=2),
    )

    # Lark checks the callback URL by sending a challenge request.
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not challenge:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Missing challenge"},
            )

        logger.info("Lark URL verification completed")
        return JSONResponse(status_code=200, content={"challenge": challenge})

    header = payload.get("header") or {}
    event_type = header.get("event_type")

    if event_type != "im.message.receive_v1":
        logger.info("Ignored unsupported event: %s", event_type)
        return JSONResponse(
            status_code=200,
            content={"ok": True, "ignored": True},
        )

    event = payload.get("event") or {}
    sender = event.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    message = event.get("message") or {}

    sender_type = sender.get("sender_type")
    open_id = sender_id.get("open_id")
    message_id = message.get("message_id")
    chat_id = message.get("chat_id")
    message_type = message.get("message_type")

    text = ""
    if message_type == "text":
        raw_content = message.get("content") or "{}"
        try:
            parsed_content = json.loads(raw_content)
            text = str(parsed_content.get("text", ""))
        except json.JSONDecodeError:
            logger.warning("Could not parse Lark message content: %s", raw_content)

    logger.info(
        "Lark message received | sender_type=%s | open_id=%s | "
        "message_id=%s | chat_id=%s | text=%r",
        sender_type,
        open_id,
        message_id,
        chat_id,
        text,
    )

    return JSONResponse(status_code=200, content={"ok": True})
