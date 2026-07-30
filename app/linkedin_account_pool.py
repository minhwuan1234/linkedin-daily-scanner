from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from app.linkedin_browser import (
    LinkedInBrowserManager,
    LinkedInBrowserSettings,
)


DEFAULT_ACCOUNT_IDS = (
    "account_01",
    "account_02",
    "account_03",
    "account_04",
    "account_05",
)

DEFAULT_PROFILE_ROOT = (
    "linkedin_browser_profiles"
)

DEFAULT_URLS_PER_ACCOUNT_TURN = 10


def _read_positive_int_env(
    key: str,
    *,
    default: int,
    maximum: int | None = None,
) -> int:
    raw_value = os.getenv(key)

    if raw_value is None:
        value = default
    else:
        try:
            value = int(
                raw_value.strip()
            )
        except ValueError as exc:
            raise ValueError(
                f"{key} must be an integer"
            ) from exc

    if value < 1:
        raise ValueError(
            f"{key} must be at least 1"
        )

    if (
        maximum is not None
        and value > maximum
    ):
        raise ValueError(
            f"{key} cannot exceed {maximum}"
        )

    return value


def _read_account_ids() -> tuple[str, ...]:
    """
    Cho phép override danh sách account qua .env.

    Ví dụ:
        LINKEDIN_ACCOUNT_IDS=account_01,account_02

    Nếu không cấu hình, mặc định dùng đủ 5 account.
    """
    raw_value = os.getenv(
        "LINKEDIN_ACCOUNT_IDS",
        "",
    ).strip()

    if not raw_value:
        return DEFAULT_ACCOUNT_IDS

    account_ids: list[str] = []
    seen: set[str] = set()

    for raw_account_id in raw_value.split(","):
        account_id = (
            raw_account_id.strip()
        )

        if not account_id:
            continue

        if account_id in seen:
            continue

        seen.add(account_id)
        account_ids.append(account_id)

    if not account_ids:
        raise ValueError(
            "LINKEDIN_ACCOUNT_IDS does not "
            "contain any valid account ID"
        )

    return tuple(account_ids)


@dataclass(frozen=True)
class LinkedInAccount:
    """
    Một account slot tương ứng với một browser profile.

    Không chứa email hoặc password.
    Session đăng nhập được lưu trong profile_directory.
    """

    account_id: str
    profile_directory: Path
    enabled: bool = True

    @property
    def exists(self) -> bool:
        return self.profile_directory.exists()

    def create_browser_settings(
        self,
    ) -> LinkedInBrowserSettings:
        base_settings = (
            LinkedInBrowserSettings
            .from_environment()
        )

        return LinkedInBrowserSettings(
            profile_directory=(
                self.profile_directory
            ),
            headless=base_settings.headless,
            navigation_timeout_ms=(
                base_settings
                .navigation_timeout_ms
            ),
            operation_timeout_ms=(
                base_settings
                .operation_timeout_ms
            ),
            slow_mo_ms=(
                base_settings.slow_mo_ms
            ),
            viewport_width=(
                base_settings.viewport_width
            ),
            viewport_height=(
                base_settings.viewport_height
            ),
        )

    def create_browser_manager(
        self,
    ) -> LinkedInBrowserManager:
        return LinkedInBrowserManager(
            settings=(
                self.create_browser_settings()
            )
        )


@dataclass(frozen=True)
class LinkedInAccountPoolSettings:
    profile_root: Path
    account_ids: tuple[str, ...]
    urls_per_account_turn: int

    @classmethod
    def from_environment(
        cls,
        project_root: Path | None = None,
    ) -> "LinkedInAccountPoolSettings":
        root = (
            project_root
            if project_root is not None
            else Path.cwd()
        )

        raw_profile_root = os.getenv(
            "LINKEDIN_ACCOUNT_PROFILE_ROOT",
            DEFAULT_PROFILE_ROOT,
        ).strip()

        profile_root = Path(
            raw_profile_root
        )

        if not profile_root.is_absolute():
            profile_root = (
                root / profile_root
            ).resolve()

        return cls(
            profile_root=profile_root,
            account_ids=_read_account_ids(),
            urls_per_account_turn=(
                _read_positive_int_env(
                    "LINKEDIN_URLS_PER_ACCOUNT_TURN",
                    default=(
                        DEFAULT_URLS_PER_ACCOUNT_TURN
                    ),
                    maximum=10,
                )
            ),
        )


class LinkedInAccountPool:
    """
    Quản lý danh sách browser sessions LinkedIn.

    _next_index giữ account sẽ được sử dụng ở lượt tiếp theo.
    Worker có thể khôi phục vị trí này từ Supabase.
    """

    def __init__(
        self,
        settings: (
            LinkedInAccountPoolSettings
            | None
        ) = None,
    ) -> None:
        self.settings = (
            settings
            if settings is not None
            else (
                LinkedInAccountPoolSettings
                .from_environment()
            )
        )

        self.accounts = tuple(
            LinkedInAccount(
                account_id=account_id,
                profile_directory=(
                    self.settings
                    .profile_root
                    / account_id
                ).resolve(),
                enabled=True,
            )
            for account_id
            in self.settings.account_ids
        )

        if not self.accounts:
            raise RuntimeError(
                "LinkedIn account pool is empty"
            )

        self._next_index = 0

    @property
    def next_account_id(self) -> str:
        return self.accounts[
            self._next_index
        ].account_id

    def validate_profiles(
        self,
    ) -> list[str]:
        errors: list[str] = []

        for account in self.accounts:
            if not account.profile_directory.exists():
                errors.append(
                    f"{account.account_id}: "
                    "profile directory does not exist"
                )
                continue

            try:
                has_files = any(
                    account.profile_directory.iterdir()
                )
            except OSError as exc:
                errors.append(
                    f"{account.account_id}: "
                    f"cannot read profile directory: {exc}"
                )
                continue

            if not has_files:
                errors.append(
                    f"{account.account_id}: "
                    "profile directory is empty"
                )

        return errors

    def get_account(
        self,
        account_id: str,
    ) -> LinkedInAccount:
        cleaned_account_id = str(
            account_id or ""
        ).strip()

        for account in self.accounts:
            if (
                account.account_id
                == cleaned_account_id
            ):
                return account

        raise KeyError(
            "LinkedIn account not found: "
            f"{cleaned_account_id}"
        )

    def get_account_index(
        self,
        account_id: str,
    ) -> int:
        cleaned_account_id = str(
            account_id or ""
        ).strip()

        for index, account in enumerate(
            self.accounts
        ):
            if (
                account.account_id
                == cleaned_account_id
            ):
                return index

        raise KeyError(
            "LinkedIn account not found: "
            f"{cleaned_account_id}"
        )

    def get_next_account(
        self,
    ) -> LinkedInAccount:
        """
        Lấy account hiện tại và dịch con trỏ sang account sau.
        """
        account = self.accounts[
            self._next_index
        ]

        self._next_index = (
            self._next_index + 1
        ) % len(self.accounts)

        return account

    def set_next_account(
        self,
        account_id: str,
    ) -> None:
        """
        Đặt account sẽ chạy ở lượt tiếp theo.
        """
        self._next_index = (
            self.get_account_index(
                account_id
            )
        )

    def set_next_after(
        self,
        account_id: str | None,
    ) -> None:
        """
        Khôi phục con trỏ từ account vừa chạy gần nhất.

        Ví dụ:
        last_account_id=account_02
        → account tiếp theo là account_03.
        """
        if not account_id:
            self._next_index = 0
            return

        try:
            last_index = self.get_account_index(
                account_id
            )
        except KeyError:
            self._next_index = 0
            return

        self._next_index = (
            last_index + 1
        ) % len(self.accounts)

    def iter_round_robin(
        self,
    ) -> Iterator[LinkedInAccount]:
        while True:
            yield self.get_next_account()

    def list_accounts(
        self,
    ) -> list[dict[str, str | bool]]:
        return [
            {
                "account_id": (
                    account.account_id
                ),
                "profile_directory": str(
                    account.profile_directory
                ),
                "profile_exists": (
                    account.exists
                ),
                "enabled": account.enabled,
            }
            for account in self.accounts
        ]
