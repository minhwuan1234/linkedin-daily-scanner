from __future__ import annotations

from dataclasses import dataclass

from app.linkedin_message_sender import (
    prepare_message_in_composer,
)
from app.linkedin_message_template import (
    build_message,
)
from app.linkedin_profile_message import (
    get_profile_name,
)
from app.outreach_account_pool import (
    OutreachAccountPool,
)


@dataclass(frozen=True)
class MessageFillInspectionResult:
    account_id: str
    linkedin_url: str
    full_name: str
    first_name: str
    final_message: str
    composer_opened: bool
    textbox_found: bool
    message_filled: bool
    send_button_found: bool


def inspect_message_fill_with_account(
    *,
    account_id: str,
    linkedin_url: str,
    template: str | None = None,
) -> MessageFillInspectionResult:
    """
    STEP 4 integration test.

    Flow:
        assigned account
        -> open profile
        -> read name
        -> build personalized message
        -> open composer
        -> fill message textbox
        -> confirm Send button exists

    IMPORTANT:
    Send is NOT clicked.
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

    browser = (
        account
        .create_browser_manager()
    )

    try:
        browser.start()

        page = browser.open_linkedin_url(
            cleaned_linkedin_url
        )

        profile_name = get_profile_name(
            page
        )

        final_message = build_message(
            first_name=(
                profile_name[
                    "first_name"
                ]
            ),
            template=template,
        )

        inspection = (
            prepare_message_in_composer(
                page,
                final_message,
            )
        )

        # Keep browser visible briefly so the user can
        # visually confirm the filled composer.
        page.wait_for_timeout(
            4_000
        )

        return MessageFillInspectionResult(
            account_id=(
                cleaned_account_id
            ),
            linkedin_url=(
                cleaned_linkedin_url
            ),
            full_name=(
                profile_name[
                    "full_name"
                ]
            ),
            first_name=(
                profile_name[
                    "first_name"
                ]
            ),
            final_message=(
                final_message
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
            message_filled=bool(
                inspection.get(
                    "message_filled"
                )
            ),
            send_button_found=bool(
                inspection.get(
                    "send_button_found"
                )
            ),
        )

    finally:
        browser.stop()


def print_message_fill_inspection(
    *,
    account_id: str,
    linkedin_url: str,
    template: str | None = None,
) -> None:
    result = (
        inspect_message_fill_with_account(
            account_id=account_id,
            linkedin_url=linkedin_url,
            template=template,
        )
    )

    print("")
    print(
        "MESSAGE FILL INSPECTION"
    )
    print(
        "======================="
    )
    print(
        f"account_id: {result.account_id}"
    )
    print(
        f"linkedin_url: {result.linkedin_url}"
    )
    print(
        f"full_name: {result.full_name}"
    )
    print(
        f"first_name: {result.first_name}"
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
        "message_filled: "
        f"{result.message_filled}"
    )
    print(
        "send_button_found: "
        f"{result.send_button_found}"
    )
    print("")
    print(
        "FINAL MESSAGE"
    )
    print(
        "-------------"
    )
    print(
        result.final_message
    )
