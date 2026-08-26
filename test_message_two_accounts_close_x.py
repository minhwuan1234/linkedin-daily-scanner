from __future__ import annotations

from app.linkedin_message_sender import send_message_once
from app.linkedin_message_template import build_message
from app.linkedin_profile_message import get_profile_name
from app.outreach_account_pool import OutreachAccountPool


MESSAGE_TEMPLATE = """Hi {first_name},

This is a message-flow test.
"""

TEST_TARGETS = [
    {
        "account_id": "outreach_account_01",
        "linkedin_url": "https://www.linkedin.com/in/frank-nguyen-flearningstudio/",
    },
    {
        "account_id": "outreach_account_02",
        "linkedin_url": "https://www.linkedin.com/in/minh-quân-851170229/
",
    },
]


def validate_target(target: dict) -> tuple[str, str]:
    account_id = str(target.get("account_id", "")).strip()
    linkedin_url = str(target.get("linkedin_url", "")).strip()

    if not account_id:
        raise ValueError("account_id is required.")

    if not linkedin_url or linkedin_url.startswith("PASTE_URL_"):
        raise ValueError(f"Missing LinkedIn URL for {account_id}.")

    return account_id, linkedin_url


def run_one(
    *,
    pool: OutreachAccountPool,
    account_id: str,
    linkedin_url: str,
) -> dict:
    account = pool.get_account(account_id)
    browser = account.create_browser_manager()

    try:
        print("")
        print("=" * 60)
        print(f"ACCOUNT: {account_id}")
        print(f"URL: {linkedin_url}")
        print("=" * 60)

        browser.start()

        page = browser.open_linkedin_url(linkedin_url)
        profile_name = get_profile_name(page)

        final_message = build_message(
            first_name=profile_name["first_name"],
            template=MESSAGE_TEMPLATE,
        )

        result = send_message_once(
            page,
            final_message,
        )

        output = {
            "account_id": account_id,
            "linkedin_url": linkedin_url,
            "full_name": profile_name["full_name"],
            "send_clicked": bool(result.get("send_clicked")),
            "composer_closed": bool(result.get("composer_closed")),
        }

        print("full_name:", output["full_name"])
        print("send_clicked:", output["send_clicked"])
        print("composer_closed:", output["composer_closed"])

        return output

    finally:
        browser.stop()


def main() -> None:
    pool = OutreachAccountPool()
    results: list[dict] = []

    for raw_target in TEST_TARGETS:
        account_id, linkedin_url = validate_target(raw_target)

        try:
            result = run_one(
                pool=pool,
                account_id=account_id,
                linkedin_url=linkedin_url,
            )
        except Exception as exc:
            result = {
                "account_id": account_id,
                "linkedin_url": linkedin_url,
                "send_clicked": False,
                "composer_closed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            print("ERROR:", result["error"])

        results.append(result)

    print("")
    print("=" * 60)
    print("TWO-ACCOUNT MESSAGE TEST RESULT")
    print("=" * 60)

    for result in results:
        print("")
        print("account_id:", result.get("account_id"))
        print("linkedin_url:", result.get("linkedin_url"))
        print("send_clicked:", result.get("send_clicked"))
        print("composer_closed:", result.get("composer_closed"))
        if result.get("error"):
            print("error:", result["error"])


if __name__ == "__main__":
    main()
