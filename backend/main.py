import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.linkedin_url_parser import (
    LinkedInUrlLimitError,
    extract_linkedin_urls_with_limit,
    get_max_urls_per_request,
)
from backend.supabase_sources import (
    insert_new_linkedin_urls,
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(
    "linkedin-daily-scanner-api"
)


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

LARK_APP_ID = os.getenv(
    "LARK_APP_ID",
    "",
).strip()

LARK_APP_SECRET = os.getenv(
    "LARK_APP_SECRET",
    "",
).strip()

LARK_VERIFICATION_TOKEN = os.getenv(
    "LARK_VERIFICATION_TOKEN",
    "",
).strip()

LARK_ENCRYPT_KEY = os.getenv(
    "LARK_ENCRYPT_KEY",
    "",
).strip()

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "",
).strip()

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY",
    "",
).strip()


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="LinkedIn Daily Scanner API",
    description=(
        "Railway backend for receiving LinkedIn URLs "
        "from Lark and storing them in Supabase."
    ),
    version="0.5.0",
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
        "timestamp": (
            datetime
            .now(timezone.utc)
            .isoformat()
        ),
        "config": {
            "lark_app_id": bool(LARK_APP_ID),
            "lark_app_secret": bool(
                LARK_APP_SECRET
            ),
            "lark_verification_token": bool(
                LARK_VERIFICATION_TOKEN
            ),
            "lark_encrypt_key": bool(
                LARK_ENCRYPT_KEY
            ),
            "supabase_url": bool(
                SUPABASE_URL
            ),
            "supabase_secret_key": bool(
                SUPABASE_SECRET_KEY
            ),
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
    Nhận text message từ Lark.

    Flow hiện tại:
    1. Nhận webhook.
    2. Lấy nội dung text.
    3. Tách LinkedIn URL.
    4. Chuẩn hóa và loại URL trùng.
    5. Reject toàn bộ request nếu vượt gateway.
    6. Thêm URL chưa tồn tại vào:
       public.linkedin_sources.linkedin_url

    Chưa thực hiện:
    - Chạy LinkedIn scraper trên Railway.
    - Gửi outbound message phản hồi về Lark.
    - Update các cột dữ liệu profile.
    """

    # -----------------------------------------------------
    # 1. READ JSON PAYLOAD
    # -----------------------------------------------------

    try:
        payload: dict[str, Any] = (
            await request.json()
        )
    except Exception:
        logger.exception(
            "Cannot parse request body as JSON"
        )

        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": (
                    "Request body must be valid JSON"
                ),
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
    # 2. LARK URL VERIFICATION
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
            and incoming_token
            != LARK_VERIFICATION_TOKEN
        ):
            logger.warning(
                "Invalid Lark verification token"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": (
                        "Invalid verification token"
                    ),
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
    # 3. CHECK EVENT TYPE
    # -----------------------------------------------------

    header = payload.get("header") or {}
    event_type = header.get("event_type")

    if event_type != "im.message.receive_v1":
        logger.info(
            "Ignored event type: %s",
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
    # 4. EXTRACT MESSAGE DATA
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
    # 5. ONLY ACCEPT USER TEXT MESSAGES
    # -----------------------------------------------------

    if sender_type and sender_type != "user":
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "ignored": True,
                "reason": "sender_is_not_user",
            },
        )

    if message_type != "text":
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "ignored": True,
                "reason": (
                    "unsupported_message_type"
                ),
            },
        )

    # -----------------------------------------------------
    # 6. PARSE MESSAGE TEXT
    # -----------------------------------------------------

    raw_content = message.get("content") or "{}"
    text = ""

    try:
        parsed_content = json.loads(raw_content)
        text = str(
            parsed_content.get("text", "")
        )
    except json.JSONDecodeError:
        logger.warning(
            "Cannot parse Lark content: %s",
            raw_content,
        )

    # -----------------------------------------------------
    # 7. EXTRACT LINKEDIN URLS + APPLY GATEWAY
    # -----------------------------------------------------

    try:
        max_urls_per_request = (
            get_max_urls_per_request()
        )

        linkedin_urls = (
            extract_linkedin_urls_with_limit(
                text
            )
        )

    except LinkedInUrlLimitError as exc:
        logger.warning(
            (
                "LINKEDIN URL REQUEST REJECTED | "
                "open_id=%s | "
                "message_id=%s | "
                "found_count=%s | "
                "max_count=%s"
            ),
            open_id,
            message_id,
            exc.found_count,
            exc.max_count,
        )

        # Trả HTTP 200 để Lark không retry cùng một event.
        # Request bị reject toàn bộ trước bước Supabase insert.
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "message_received": True,
                "urls_inserted": False,
                "reason": (
                    "linkedin_url_limit_exceeded"
                ),
                "message_id": message_id,
                "open_id": open_id,
                "found_count": exc.found_count,
                "max_count": exc.max_count,
                "error": (
                    "Too many LinkedIn URLs in "
                    "one message."
                ),
            },
        )

    except ValueError as exc:
        logger.exception(
            "Invalid LinkedIn URL gateway configuration"
        )

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message_received": True,
                "urls_inserted": False,
                "reason": (
                    "invalid_url_gateway_configuration"
                ),
                "error": str(exc),
            },
        )

    logger.info(
        (
            "LARK MESSAGE PARSED | "
            "open_id=%s | "
            "message_id=%s | "
            "chat_id=%s | "
            "chat_type=%s | "
            "url_count=%s | "
            "max_urls_per_request=%s | "
            "urls=%s"
        ),
        open_id,
        message_id,
        chat_id,
        chat_type,
        len(linkedin_urls),
        max_urls_per_request,
        json.dumps(
            linkedin_urls,
            ensure_ascii=False,
        ),
    )

    if not linkedin_urls:
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "message_received": True,
                "urls_inserted": False,
                "reason": (
                    "no_linkedin_urls_found"
                ),
                "message_id": message_id,
                "open_id": open_id,
                "url_count": 0,
                "max_urls_per_request": (
                    max_urls_per_request
                ),
            },
        )

    # -----------------------------------------------------
    # 8. INSERT URLS INTO SUPABASE
    # -----------------------------------------------------

    try:
        result = insert_new_linkedin_urls(
    linkedin_urls,
    chat_id=chat_id,
    message_id=message_id,
    sender_open_id=open_id,
)
    except Exception as exc:
        logger.exception(
            (
                "Could not insert LinkedIn URLs "
                "into Supabase"
            )
        )

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": (
                    "Could not insert LinkedIn URLs"
                ),
                "detail": str(exc),
            },
        )

    inserted_urls = [
        row.get("linkedin_url")
        for row in result.inserted
        if row.get("linkedin_url")
    ]

    logger.info(
        (
            "LINKEDIN SOURCES UPDATED | "
            "message_id=%s | "
            "inserted_count=%s | "
            "existing_count=%s | "
            "inserted_urls=%s"
        ),
        message_id,
        result.inserted_count,
        result.existing_count,
        json.dumps(
            inserted_urls,
            ensure_ascii=False,
        ),
    )

    # -----------------------------------------------------
    # 9. RESPONSE TO LARK
    # -----------------------------------------------------

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message_received": True,
            "message_id": message_id,
            "open_id": open_id,
            "received_url_count": len(
                linkedin_urls
            ),
            "max_urls_per_request": (
                max_urls_per_request
            ),
            "inserted_count": (
                result.inserted_count
            ),
            "existing_count": (
                result.existing_count
            ),
            "inserted_urls": inserted_urls,
            "existing_urls": (
                result.existing_urls
            ),
        },
    )
