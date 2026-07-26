import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.linkedin_url_parser import (
    detect_linkedin_source_type,
    extract_linkedin_urls,
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("linkedin-daily-scanner-api")


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

LARK_APP_ID = os.getenv("LARK_APP_ID", "").strip()
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "").strip()
LARK_VERIFICATION_TOKEN = os.getenv(
    "LARK_VERIFICATION_TOKEN",
    "",
).strip()
LARK_ENCRYPT_KEY = os.getenv("LARK_ENCRYPT_KEY", "").strip()


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="LinkedIn Daily Scanner API",
    description="Railway backend for Lark webhook and LinkedIn scan jobs.",
    version="0.3.0",
)


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "linkedin-daily-scanner-api",
        "status": "running",
    }


@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lark_config": {
            "app_id_configured": bool(LARK_APP_ID),
            "app_secret_configured": bool(LARK_APP_SECRET),
            "verification_token_configured": bool(
                LARK_VERIFICATION_TOKEN
            ),
            "encrypt_key_configured": bool(LARK_ENCRYPT_KEY),
        },
    }


# =========================================================
# LARK WEBHOOK
# =========================================================

@app.post("/webhooks/lark/events")
async def receive_lark_event(
    request: Request,
) -> JSONResponse:
    """
    Nhận event từ Lark và tách LinkedIn URL từ text message.

    Step 3:
    - Nhận event.
    - Trả URL verification challenge.
    - Lấy open_id, message_id, chat_id.
    - Parse nội dung text.
    - Tách LinkedIn URL.
    - Chuẩn hóa URL.
    - Loại URL trùng.

    Chưa:
    - Ghi job vào Supabase.
    - Chạy LinkedIn scraper.
    - Gửi kết quả về Lark.
    """

    # -----------------------------------------------------
    # 1. ĐỌC PAYLOAD
    # -----------------------------------------------------

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        logger.exception("Cannot parse request body as JSON")

        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "Request body must be valid JSON",
            },
        )

    logger.info(
        "LARK EVENT RECEIVED:\n%s",
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
    )

    # -----------------------------------------------------
    # 2. URL VERIFICATION
    # -----------------------------------------------------

    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")

        if not challenge:
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "error": "Missing challenge",
                },
            )

        incoming_token = payload.get("token")

        if (
            LARK_VERIFICATION_TOKEN
            and incoming_token
            and incoming_token != LARK_VERIFICATION_TOKEN
        ):
            logger.warning(
                "Invalid Lark verification token"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": "Invalid verification token",
                },
            )

        logger.info("Lark URL verification successful")

        return JSONResponse(
            status_code=200,
            content={
                "challenge": challenge,
            },
        )

    # -----------------------------------------------------
    # 3. KIỂM TRA EVENT TYPE
    # -----------------------------------------------------

    header = payload.get("header") or {}
    event_type = header.get("event_type")

    if event_type != "im.message.receive_v1":
        logger.info(
            "Ignored unsupported event: %s",
            event_type,
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "ignored": True,
                "event_type": event_type,
            },
        )

    # -----------------------------------------------------
    # 4. LẤY MESSAGE DATA
    # -----------------------------------------------------

    event = payload.get("event") or {}
    sender = event.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    message = event.get("message") or {}

    sender_type = sender.get("sender_type")
    open_id = sender_id.get("open_id")
    message_id = message.get("message_id")
    chat_id = message.get("chat_id")
    chat_type = message.get("chat_type")
    message_type = message.get("message_type")

    # -----------------------------------------------------
    # 5. BỎ QUA EVENT KHÔNG PHẢI USER
    # -----------------------------------------------------

    if sender_type and sender_type != "user":
        logger.info(
            "Ignored sender type: %s",
            sender_type,
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "ignored": True,
                "reason": "sender_is_not_user",
            },
        )

    # -----------------------------------------------------
    # 6. CHỈ NHẬN TEXT MESSAGE
    # -----------------------------------------------------

    if message_type != "text":
        logger.info(
            "Ignored message type: %s",
            message_type,
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "ignored": True,
                "reason": "unsupported_message_type",
            },
        )

    # -----------------------------------------------------
    # 7. PARSE TEXT
    # -----------------------------------------------------

    raw_content = message.get("content") or "{}"
    text = ""

    try:
        parsed_content = json.loads(raw_content)
        text = parsed_content.get("text", "")
    except json.JSONDecodeError:
        logger.warning(
            "Cannot parse Lark message content: %s",
            raw_content,
        )

    # -----------------------------------------------------
    # 8. TÁCH LINKEDIN URL
    # -----------------------------------------------------

    linkedin_urls = extract_linkedin_urls(text)

    url_results = [
        {
            "url": url,
            "source_type": detect_linkedin_source_type(url),
        }
        for url in linkedin_urls
    ]

    # -----------------------------------------------------
    # 9. LOG KẾT QUẢ
    # -----------------------------------------------------

    logger.info(
        (
            "LARK MESSAGE PARSED | "
            "open_id=%s | "
            "message_id=%s | "
            "chat_id=%s | "
            "chat_type=%s | "
            "url_count=%s | "
            "urls=%s"
        ),
        open_id,
        message_id,
        chat_id,
        chat_type,
        len(linkedin_urls),
        json.dumps(
            url_results,
            ensure_ascii=False,
        ),
    )

    # -----------------------------------------------------
    # 10. RESPONSE
    # -----------------------------------------------------

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "event_type": event_type,
            "message_received": True,
            "message_id": message_id,
            "open_id": open_id,
            "chat_id": chat_id,
            "text": text,
            "url_count": len(linkedin_urls),
            "urls": url_results,
        },
    )
