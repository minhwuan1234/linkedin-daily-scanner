from __future__ import annotations

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


# =========================================================
# MESSAGE WORKER FLOW TEST — ACCOUNT 02 ONLY
# =========================================================
#
# This mirrors the deployed worker's per-account flow:
#
# one assigned account
# -> start ONE persistent browser session
# -> process target 1
# -> send
# -> close composer
# -> process target 2
# -> send
# -> close composer
# -> stop browser
#
# Supabase is NOT read or updated by this test.
#
# IMPORTANT:
# This performs REAL LinkedIn message sends.
# =========================================================


ACCOUNT_ID = "outreach_account_02"

MESSAGE_TEMPLATE = """Hi {first_name},

This is a message-flow test.
"""


TEST_URLS = [
    "https://www.linkedin.com/in/minh-quân-851170229/",
    "https://www.linkedin.com/in/frank-nguyen-flearningstudio/",
    "https://www.linkedin.com/in/linh-nguyen-huyen-6070a530a/"
]


def validate_urls() -> list[str]:
    cleaned_urls: list[str] = []

    for index, raw_url in enumerate(
        TEST_URLS,
        start=1,
    ):
        url = str(
            raw_url
            or ""
        ).strip()

        if (
            not url
            or url.startswith(
                "PASTE_URL_"
            )
        ):
            raise ValueError(
                f"Missing LinkedIn URL #{index}."
            )

        cleaned_urls.append(
            url
        )

    return cleaned_urls


def process_one_target(
    *,
    browser,
    linkedin_url: str,
) -> dict:
    page = browser.open_linkedin_url(
        linkedin_url
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
        template=MESSAGE_TEMPLATE,
    )

    send_result = send_message_once(
        page,
        final_message,
        expected_profile_name=(
            profile_name[
                "full_name"
            ]
        ),
    )

    # Same success boundary as the deployed message worker:
    # a successful Send click means the message is treated as sent.
    if not bool(
        send_result.get(
            "send_clicked"
        )
    ):
        raise RuntimeError(
            "Message Send button was not clicked."
        )

    return {
        "linkedin_url": (
            linkedin_url
        ),
        "full_name": (
            profile_name[
                "full_name"
            ]
        ),
        "first_name": (
            profile_name[
                "first_name"
            ]
        ),
        "send_clicked": bool(
            send_result.get(
                "send_clicked"
            )
        ),
        "composer_closed": bool(
            send_result.get(
                "composer_closed"
            )
        ),
        "message_text": (
            final_message
        ),
    }


def main() -> None:
    urls = validate_urls()

    pool = OutreachAccountPool()

    account = pool.get_account(
        ACCOUNT_ID
    )

    browser = (
        account
        .create_browser_manager()
    )

    results: list[dict] = []

    print("")
    print("=" * 64)
    print("MESSAGE WORKER FLOW TEST")
    print("=" * 64)
    print(
        "account_id:",
        ACCOUNT_ID,
    )
    print(
        "targets:",
        len(urls),
    )

    try:
        # IMPORTANT:
        # browser starts ONCE for account 02,
        # matching the deployed worker's account-group behavior.
        browser.start()

        for index, linkedin_url in enumerate(
            urls,
            start=1,
        ):
            print("")
            print("-" * 64)
            print(
                f"TARGET {index}/{len(urls)}"
            )
            print(
                "url:",
                linkedin_url,
            )

            try:
                result = process_one_target(
                    browser=browser,
                    linkedin_url=linkedin_url,
                )

                result[
                    "ok"
                ] = True

                print(
                    "full_name:",
                    result[
                        "full_name"
                    ],
                )
                print(
                    "send_clicked:",
                    result[
                        "send_clicked"
                    ],
                )
                print(
                    "composer_closed:",
                    result[
                        "composer_closed"
                    ],
                )

            except Exception as exc:
                result = {
                    "ok": False,
                    "linkedin_url": (
                        linkedin_url
                    ),
                    "send_clicked": False,
                    "composer_closed": False,
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                }

                print(
                    "ERROR:",
                    result[
                        "error"
                    ],
                )

            results.append(
                result
            )

    finally:
        browser.stop()

    print("")
    print("=" * 64)
    print("FINAL RESULT")
    print("=" * 64)

    for index, result in enumerate(
        results,
        start=1,
    ):
        print("")
        print(
            f"target_{index}:",
            result.get(
                "linkedin_url"
            ),
        )
        print(
            "ok:",
            result.get(
                "ok"
            ),
        )
        print(
            "send_clicked:",
            result.get(
                "send_clicked"
            ),
        )
        print(
            "composer_closed:",
            result.get(
                "composer_closed"
            ),
        )

        if result.get(
            "error"
        ):
            print(
                "error:",
                result[
                    "error"
                ],
            )


if __name__ == "__main__":
    main()
