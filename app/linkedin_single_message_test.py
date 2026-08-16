from __future__ import annotations

from dataclasses import dataclass

from app.linkedin_message_sender import (
    send_message_once,
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
class SingleMessageSendResult:
    account_id: str
    linkedin_url: str
    full_name: str
    first_name: str
    final_message: str
    sent_verified: bool


def send_single_test_message(
    *,
    account_id: str,
    linkedin_url: str,
    template: str,
) -> SingleMessageSendResult:
    """
    STEP 5 manual integration test.

    WARNING:
    This performs ONE real LinkedIn message send.

    No Supabase status is changed yet.
    """

    cleaned_account_id = str(
        account_id
        or ""
    ).strip()

    cleaned_linkedin_url = str(
        linkedin_url
        or ""
    ).strip()

    cleaned_template = str(
        template
        or ""
    )

    if not cleaned_account_id:
        raise ValueError(
            "account_id is required."
        )

    if not cleaned_linkedin_url:
        raise ValueError(
            "linkedin_url is required."
        )

    if not cleaned_template.strip():
        raise ValueError(
            "template is required."
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
            template=(
                cleaned_template
            ),
        )

        result = send_message_once(
            page,
            final_message,
        )

        page.wait_for_timeout(
            2_000
        )

        return SingleMessageSendResult(
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
            sent_verified=bool(
                result.get(
                    "sent_verified"
                )
            ),
        )

    finally:
        browser.stop()


def print_single_test_message(
    *,
    account_id: str,
    linkedin_url: str,
    template: str,
) -> None:
    result = send_single_test_message(
        account_id=account_id,
        linkedin_url=linkedin_url,
        template=template,
    )

    print("")
    print(
        "SINGLE MESSAGE SEND TEST"
    )
    print(
        "========================"
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
        f"sent_verified: {result.sent_verified}"
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
