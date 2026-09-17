from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import requests


LARK_BASE_URL = "https://open.larksuite.com"

TENANT_TOKEN_URL = (
    f"{LARK_BASE_URL}"
    "/open-apis/auth/v3/"
    "tenant_access_token/internal"
)

SEND_MESSAGE_URL = (
    f"{LARK_BASE_URL}"
    "/open-apis/im/v1/messages"
)

DEFAULT_REQUEST_TIMEOUT_SECONDS = 20
DEFAULT_TOKEN_REFRESH_BUFFER_SECONDS = 300
MAX_MESSAGE_LENGTH = 12_000


class LarkClientError(RuntimeError):
    """
    Base error cho Lark API client.
    """


class LarkConfigurationError(
    LarkClientError
):
    """
    Thiếu hoặc sai cấu hình Lark.
    """


class LarkApiError(
    LarkClientError
):
    """
    Lark API trả về lỗi.
    """

    def __init__(
        self,
        *,
        operation: str,
        code: int | None,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        self.operation = operation
        self.code = code
        self.message = message
        self.status_code = status_code
        self.response_data = (
            response_data or {}
        )

        super().__init__(
            f"{operation} failed | "
            f"status={status_code} | "
            f"code={code} | "
            f"message={message}"
        )


@dataclass(frozen=True)
class LarkClientSettings:
    app_id: str
    app_secret: str
    request_timeout_seconds: int
    token_refresh_buffer_seconds: int

    @classmethod
    def from_environment(
        cls,
    ) -> "LarkClientSettings":
        app_id = os.getenv(
            "LARK_APP_ID",
            "",
        ).strip()

        app_secret = os.getenv(
            "LARK_APP_SECRET",
            "",
        ).strip()

        if not app_id:
            raise LarkConfigurationError(
                "Missing LARK_APP_ID"
            )

        if not app_secret:
            raise LarkConfigurationError(
                "Missing LARK_APP_SECRET"
            )

        return cls(
            app_id=app_id,
            app_secret=app_secret,
            request_timeout_seconds=(
                _read_positive_int_env(
                    "LARK_REQUEST_TIMEOUT_SECONDS",
                    default=(
                        DEFAULT_REQUEST_TIMEOUT_SECONDS
                    ),
                )
            ),
            token_refresh_buffer_seconds=(
                _read_non_negative_int_env(
                    "LARK_TOKEN_REFRESH_BUFFER_SECONDS",
                    default=(
                        DEFAULT_TOKEN_REFRESH_BUFFER_SECONDS
                    ),
                )
            ),
        )


@dataclass(frozen=True)
class LarkMessageResult:
    message_id: str | None
    chat_id: str | None
    raw_data: dict[str, Any]


def _read_positive_int_env(
    key: str,
    *,
    default: int,
) -> int:
    raw_value = os.getenv(key)

    if raw_value is None:
        return default

    try:
        value = int(
            raw_value.strip()
        )
    except ValueError as exc:
        raise LarkConfigurationError(
            f"{key} must be an integer"
        ) from exc

    if value < 1:
        raise LarkConfigurationError(
            f"{key} must be at least 1"
        )

    return value


def _read_non_negative_int_env(
    key: str,
    *,
    default: int,
) -> int:
    raw_value = os.getenv(key)

    if raw_value is None:
        return default

    try:
        value = int(
            raw_value.strip()
        )
    except ValueError as exc:
        raise LarkConfigurationError(
            f"{key} must be an integer"
        ) from exc

    if value < 0:
        raise LarkConfigurationError(
            f"{key} cannot be negative"
        )

    return value


def _as_clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _truncate_message(
    text: str,
    *,
    max_length: int = MAX_MESSAGE_LENGTH,
) -> str:
    cleaned = _as_clean_text(text)

    if len(cleaned) <= max_length:
        return cleaned

    suffix = (
        "\n\n[Message truncated because "
        "it exceeded the safe length.]"
    )

    available_length = max(
        0,
        max_length - len(suffix)
    )

    return (
        cleaned[:available_length]
        + suffix
    )


class LarkClient:
    """
    Client tối thiểu để gửi text message qua Lark Bot.

    Token được cache trong process và refresh trước khi
    hết hạn.
    """

    def __init__(
        self,
        settings: LarkClientSettings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.settings = (
            settings
            if settings is not None
            else LarkClientSettings.from_environment()
        )

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        self._tenant_access_token: str | None = None
        self._tenant_token_expires_at = 0.0

    def get_tenant_access_token(
        self,
        *,
        force_refresh: bool = False,
    ) -> str:
        """
        Lấy hoặc tái sử dụng tenant_access_token.
        """
        current_time = time.time()

        token_is_usable = (
            self._tenant_access_token
            and current_time
            < self._tenant_token_expires_at
        )

        if (
            token_is_usable
            and not force_refresh
        ):
            return str(
                self._tenant_access_token
            )

        payload = {
            "app_id": self.settings.app_id,
            "app_secret": (
                self.settings.app_secret
            ),
        }

        try:
            response = self.session.post(
                TENANT_TOKEN_URL,
                json=payload,
                headers={
                    "Content-Type": (
                        "application/json; "
                        "charset=utf-8"
                    ),
                },
                timeout=(
                    self.settings
                    .request_timeout_seconds
                ),
            )
        except requests.RequestException as exc:
            raise LarkApiError(
                operation=(
                    "get_tenant_access_token"
                ),
                code=None,
                message=str(exc),
            ) from exc

        data = _read_json_response(
            response=response,
            operation=(
                "get_tenant_access_token"
            ),
        )

        code = data.get("code")

        if code != 0:
            raise LarkApiError(
                operation=(
                    "get_tenant_access_token"
                ),
                code=_as_optional_int(code),
                message=_as_clean_text(
                    data.get("msg")
                )
                or "Unknown Lark token error",
                status_code=response.status_code,
                response_data=data,
            )

        token = _as_clean_text(
            data.get("tenant_access_token")
        )

        if not token:
            raise LarkApiError(
                operation=(
                    "get_tenant_access_token"
                ),
                code=0,
                message=(
                    "Lark response did not contain "
                    "tenant_access_token"
                ),
                status_code=response.status_code,
                response_data=data,
            )

        expire_seconds = (
            _as_optional_int(
                data.get("expire")
            )
            or 7200
        )

        refresh_buffer = min(
            self.settings
            .token_refresh_buffer_seconds,
            max(
                0,
                expire_seconds - 60,
            ),
        )

        usable_seconds = max(
            60,
            expire_seconds - refresh_buffer,
        )

        self._tenant_access_token = token
        self._tenant_token_expires_at = (
            current_time + usable_seconds
        )

        return token

    def send_text_to_chat(
        self,
        *,
        chat_id: str,
        text: str,
        deduplication_key: str | None = None,
    ) -> LarkMessageResult:
        """
        Gửi text vào đúng chat Lark.

        Retry đúng một lần nếu request đầu tiên có dấu hiệu
        token hết hạn hoặc token không hợp lệ.
        """
        cleaned_chat_id = _as_clean_text(
            chat_id
        )

        if not cleaned_chat_id:
            raise ValueError(
                "chat_id cannot be empty"
            )

        cleaned_text = _truncate_message(
            text
        )

        if not cleaned_text:
            raise ValueError(
                "Lark message text cannot be empty"
            )

        request_uuid = (
            _build_request_uuid(
                deduplication_key
            )
        )

        return self._send_text_request(
            chat_id=cleaned_chat_id,
            text=cleaned_text,
            request_uuid=request_uuid,
            allow_token_retry=True,
        )

    def _send_text_request(
        self,
        *,
        chat_id: str,
        text: str,
        request_uuid: str,
        allow_token_retry: bool,
    ) -> LarkMessageResult:
        token = self.get_tenant_access_token()

        body = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps(
                {
                    "text": text,
                },
                ensure_ascii=False,
            ),
            "uuid": request_uuid,
        }

        try:
            response = self.session.post(
                SEND_MESSAGE_URL,
                params={
                    "receive_id_type": (
                        "chat_id"
                    ),
                },
                json=body,
                headers={
                    "Authorization": (
                        f"Bearer {token}"
                    ),
                    "Content-Type": (
                        "application/json; "
                        "charset=utf-8"
                    ),
                },
                timeout=(
                    self.settings
                    .request_timeout_seconds
                ),
            )
        except requests.RequestException as exc:
            raise LarkApiError(
                operation="send_message",
                code=None,
                message=str(exc),
            ) from exc

        data = _read_json_response(
            response=response,
            operation="send_message",
        )

        code = _as_optional_int(
            data.get("code")
        )

        if code != 0:
            if (
                allow_token_retry
                and _looks_like_token_error(
                    status_code=(
                        response.status_code
                    ),
                    code=code,
                    message=_as_clean_text(
                        data.get("msg")
                    ),
                )
            ):
                self._tenant_access_token = None
                self._tenant_token_expires_at = 0

                self.get_tenant_access_token(
                    force_refresh=True
                )

                return self._send_text_request(
                    chat_id=chat_id,
                    text=text,
                    request_uuid=request_uuid,
                    allow_token_retry=False,
                )

            raise LarkApiError(
                operation="send_message",
                code=code,
                message=_as_clean_text(
                    data.get("msg")
                )
                or "Unknown Lark message error",
                status_code=response.status_code,
                response_data=data,
            )

        response_data = data.get("data")

        if not isinstance(
            response_data,
            dict,
        ):
            response_data = {}

        message = response_data.get(
            "message"
        )

        if not isinstance(message, dict):
            message = {}

        return LarkMessageResult(
            message_id=(
                _as_clean_text(
                    message.get("message_id")
                )
                or None
            ),
            chat_id=(
                _as_clean_text(
                    message.get("chat_id")
                )
                or chat_id
            ),
            raw_data=data,
        )


def _read_json_response(
    *,
    response: requests.Response,
    operation: str,
) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        body_preview = (
            response.text or ""
        )[:500]

        raise LarkApiError(
            operation=operation,
            code=None,
            message=(
                "Lark returned a non-JSON response: "
                f"{body_preview}"
            ),
            status_code=response.status_code,
        ) from exc

    if not isinstance(data, dict):
        raise LarkApiError(
            operation=operation,
            code=None,
            message=(
                "Lark returned an unexpected "
                "JSON response"
            ),
            status_code=response.status_code,
        )

    return data


def _as_optional_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _looks_like_token_error(
    *,
    status_code: int,
    code: int | None,
    message: str,
) -> bool:
    if status_code in {
        401,
        403,
    }:
        return True

    normalized_message = (
        message.casefold()
    )

    token_terms = (
        "token",
        "unauthorized",
        "authorization",
        "access denied",
    )

    return any(
        term in normalized_message
        for term in token_terms
    )


def _build_request_uuid(
    deduplication_key: str | None,
) -> str:
    """
    Lark cho phép uuid tối đa 50 ký tự để chống gửi trùng.

    Nếu có key ổn định, tạo UUID5 từ key đó.
    Nếu không có, dùng UUID4.
    """
    cleaned_key = _as_clean_text(
        deduplication_key
    )

    if cleaned_key:
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                cleaned_key,
            )
        )

    return str(
        uuid.uuid4()
    )


def send_lark_text_message(
    *,
    chat_id: str,
    text: str,
    deduplication_key: str | None = None,
    client: LarkClient | None = None,
) -> LarkMessageResult:
    """
    Helper function để worker gọi.
    """
    resolved_client = (
        client
        if client is not None
        else LarkClient()
    )

    return resolved_client.send_text_to_chat(
        chat_id=chat_id,
        text=text,
        deduplication_key=(
            deduplication_key
        ),
    )
