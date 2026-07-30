from __future__ import annotations

import re
from dataclasses import dataclass

from app.lark_client import LarkClient
from app.settings import load_settings
from backend.health_check_service import (
    LinkedInSystemHealthCheck,
)


HEALTH_CHECK_COMMANDS = {
    "health check",
    "healthcheck",
    "system status",
    "status",
}


def _normalise_command(
    text: str | None,
) -> str:
    value = str(
        text or ""
    ).strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def is_health_check_command(
    text: str | None,
) -> bool:
    return (
        _normalise_command(text)
        in HEALTH_CHECK_COMMANDS
    )


@dataclass(frozen=True)
class LarkCommandResult:
    handled: bool
    command: str | None = None
    response_text: str | None = None
    message_id: str | None = None


def handle_lark_command(
    *,
    text: str | None,
    chat_id: str | None,
) -> LarkCommandResult:
    """
    Handle supported text commands from the Lark webhook.

    Returns handled=False when the message is not a command.
    The caller can then continue with the LinkedIn URL flow.
    """
    command = _normalise_command(
        text
    )

    if command not in HEALTH_CHECK_COMMANDS:
        return LarkCommandResult(
            handled=False
        )

    cleaned_chat_id = str(
        chat_id or ""
    ).strip()

    if not cleaned_chat_id:
        raise ValueError(
            "chat_id is required for "
            "the health check command"
        )

    settings = load_settings()

    health_result = (
        LinkedInSystemHealthCheck(
            settings=settings
        )
        .run()
    )

    lark_client = LarkClient()

    send_result = (
        lark_client.send_text_to_chat(
            chat_id=cleaned_chat_id,
            text=health_result.message,
            deduplication_key=None,
        )
    )

    return LarkCommandResult(
        handled=True,
        command="health check",
        response_text=(
            health_result.message
        ),
        message_id=(
            send_result.message_id
        ),
    )
