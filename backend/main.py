import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("lark-webhook")

app = FastAPI()


@app.post("/webhooks/lark/events")
async def receive_lark_event(request: Request) -> JSONResponse:
    payload = await request.json()

    logger.info(
        "LARK EVENT RECEIVED:\n%s",
        json.dumps(payload, ensure_ascii=False, indent=2),
    )

    # Lark kiểm tra webhook URL.
    if payload.get("type") == "url_verification":
        return JSONResponse(
            status_code=200,
            content={
                "challenge": payload.get("challenge"),
            },
        )

    header = payload.get("header") or {}
    event_type = header.get("event_type")

    logger.info("Lark event type: %s", event_type)

    if event_type == "im.message.receive_v1":
        event = payload.get("event") or {}
        sender = event.get("sender") or {}
        sender_id = sender.get("sender_id") or {}
        message = event.get("message") or {}

        raw_content = message.get("content") or "{}"

        try:
            content = json.loads(raw_content)
        except json.JSONDecodeError:
            content = {}

        logger.info(
            (
                "LARK MESSAGE | open_id=%s | "
                "message_id=%s | chat_id=%s | text=%r"
            ),
            sender_id.get("open_id"),
            message.get("message_id"),
            message.get("chat_id"),
            content.get("text", ""),
        )

    return JSONResponse(
        status_code=200,
        content={"ok": True},
    )
