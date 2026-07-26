import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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
    version="0.2.0",
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
    """
    Kiểm tra Railway backend có đang hoạt động không.

    Chỉ trả true/false cho cấu hình Lark,
    không trả secret thật ra ngoài.
    """
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
    Nhận event từ Lark.

    Hiện tại endpoint này thực hiện:
    1. Nhận JSON payload.
    2. Log toàn bộ payload trên Railway.
    3. Trả challenge khi Lark verify webhook.
    4. Nhận event im.message.receive_v1.
    5. Lấy open_id, message_id, chat_id và nội dung text.
    6. Trả HTTP 200 cho Lark.

    Chưa:
    - Chạy LinkedIn scraper.
    - Ghi job vào Supabase.
    - Gửi tin nhắn trả lại user.
    """

    # -----------------------------------------------------
    # 1. ĐỌC REQUEST JSON
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

    # -----------------------------------------------------
    # 2. LOG TOÀN BỘ PAYLOAD
    # -----------------------------------------------------

    logger.info(
        "LARK EVENT RECEIVED:\n%s",
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
    )

    # -----------------------------------------------------
    # 3. XỬ LÝ URL VERIFICATION
    # -----------------------------------------------------

    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")

        if not challenge:
            logger.warning(
                "Lark URL verification request has no challenge"
            )

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
                "Invalid Lark verification token during URL verification"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": "Invalid verification token",
                },
            )

        logger.info(
            "Lark URL verification successful"
        )

        return JSONResponse(
            status_code=200,
            content={
                "challenge": challenge,
            },
        )

    # -----------------------------------------------------
    # 4. XÁC ĐỊNH EVENT TYPE
    # -----------------------------------------------------

    header = payload.get("header") or {}
    event_type = header.get("event_type")

    logger.info(
        "Lark event type: %s",
        event_type or "unknown",
    )

    # Bỏ qua các event chưa được support.
    if event_type != "im.message.receive_v1":
        logger.info(
            "Ignored unsupported Lark event: %s",
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
    # 5. LẤY EVENT DATA
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
    # 6. BỎ QUA MESSAGE KHÔNG PHẢI TỪ USER
    # -----------------------------------------------------

    if sender_type and sender_type != "user":
        logger.info(
            "Ignored message from non-user sender: %s",
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
    # 7. CHỈ XỬ LÝ TEXT MESSAGE
    # -----------------------------------------------------

    if message_type != "text":
        logger.info(
            "Ignored unsupported message type: %s",
            message_type,
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "ignored": True,
                "reason": "unsupported_message_type",
                "message_type": message_type,
            },
        )

    # -----------------------------------------------------
    # 8. PARSE NỘI DUNG TEXT
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
    # 9. LOG MESSAGE ĐÃ PARSE
    # -----------------------------------------------------

    logger.info(
        (
            "LARK MESSAGE RECEIVED | "
            "open_id=%s | "
            "message_id=%s | "
            "chat_id=%s | "
            "chat_type=%s | "
            "text=%r"
        ),
        open_id,
        message_id,
        chat_id,
        chat_type,
        text,
    )

    # -----------------------------------------------------
    # 10. RESPONSE CHO LARK
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
        },
    )
