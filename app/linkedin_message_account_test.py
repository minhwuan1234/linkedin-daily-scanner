from __future__ import annotations

from dataclasses import dataclass

from app.linkedin_message_sender import (
    inspect_message_composer,
)
from app.outreach_account_pool import (
    OutreachAccountPool,
)


@dataclass(frozen=True)
class MessageComposerInspectionResult:
    account_id: str
    linkedin_url: str
    composer_opened: bool
    textbox_found: bool
    send_button_found: bool

    @property
    def ready(self) -> bool:
        return (
            self.composer_opened
            and self.textbox_found
            and self.send_button_found
        )


def inspect_message_profile_with_account(
    *,
    account_id: str,
    linkedin_url: str,
) -> MessageComposerInspectionResult:
    """
    STEP 2 — connect message-composer logic to the current
    Outreach account/browser system.

    Flow:
        assigned_account_id
        -> OutreachAccountPool.get_account()
        -> account.create_browser_manager()
        -> browser.start()
        -> browser.open_linkedin_url()
        -> inspect_message_composer()
        -> browser.stop()

    IMPORTANT:
    This function still DOES NOT send a message.

    It only proves that:
    1. the exact assigned Outreach account can be opened;
    2. the target LinkedIn profile can be opened;
    3. the Message composer can be opened;
    4. textbox can be found;
    5. Send button can be found.
    """

    cleaned_account_id = str(
        account_id
        or ""
    ).strip()

    cleaned_linkedin_url = str(
        linkedin_url
        or ""
    ).strip()

    if not cleaned_account_id:
        raise ValueError(
            "account_id is required."
        )

    if not cleaned_linkedin_url:
        raise ValueError(
            "linkedin_url is required."
        )

    pool = OutreachAccountPool()

    account = pool.get_account(
        cleaned_account_id
    )

    if not account.enabled:
        raise RuntimeError(
            "Outreach account is disabled: "
            f"{cleaned_account_id}"
        )

    if not account.exists:
        raise RuntimeError(
            "Outreach browser profile does not exist: "
            f"{account.profile_directory}"
        )

    browser = (
        account
        .create_browser_manager()
    )

    try:
        browser.start()

        page = browser.open_linkedin_url(
            cleaned_linkedin_url
        )

        inspection = (
            inspect_message_composer(
                page
            )
        )

        return (
            MessageComposerInspectionResult(
                account_id=(
                    cleaned_account_id
                ),
                linkedin_url=(
                    cleaned_linkedin_url
                ),
                composer_opened=bool(
                    inspection.get(
                        "composer_opened"
                    )
                ),
                textbox_found=bool(
                    inspection.get(
                        "textbox_found"
                    )
                ),
                send_button_found=bool(
                    inspection.get(
                        "send_button_found"
                    )
                ),
            )
        )

    finally:
        browser.stop()


def print_message_profile_inspection(
    *,
    account_id: str,
    linkedin_url: str,
) -> None:
    """
    Small manual-test helper.

    Example from a local Python shell:

        from app.linkedin_message_account_test import (
            print_message_profile_inspection,
        )

        print_message_profile_inspection(
            account_id="outreach_account_02",
            linkedin_url="https://www.linkedin.com/in/...",
        )

    This DOES NOT send anything.
    """

    result = (
        inspect_message_profile_with_account(
            account_id=account_id,
            linkedin_url=linkedin_url,
        )
    )

    print("")
    print(
        "MESSAGE COMPOSER INSPECTION"
    )
    print(
        "==========================="
    )
    print(
        f"account_id: {result.account_id}"
    )
    print(
        f"linkedin_url: {result.linkedin_url}"
    )
    print(
        "composer_opened: "
        f"{result.composer_opened}"
    )
    print(
        "textbox_found: "
        f"{result.textbox_found}"
    )
    print(
        "send_button_found: "
        f"{result.send_button_found}"
    )
    print(
        f"ready: {result.ready}"
    )
