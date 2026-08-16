from __future__ import annotations

from playwright.sync_api import (
    Locator,
    Page,
)


# =========================================================
# STEP 1 — MESSAGE COMPOSER DISCOVERY
# =========================================================
#
# Mục tiêu của file này ở step hiện tại:
#
# LinkedIn profile page
# -> scroll đúng container
# -> tìm đúng profile Message action
# -> mở messaging composer
# -> tìm textbox
# -> tìm Send button
#
# CHƯA:
# - build template
# - fill message
# - click Send
# - verify sent
# - update Supabase
# - dùng worker / batch
#
# File chỉ phụ thuộc vào Playwright Page.
# Browser/account sẽ được truyền từ Outreach system hiện tại.
# =========================================================



def assert_profile_page_available(
    page: Page,
) -> None:
    """
    Stop early when LinkedIn did not open a usable profile page.

    This prevents a misleading downstream error such as:
        "Visible LinkedIn profile Message action was not found."

    when the real problem is:
        - 404 / Page not found
        - profile unavailable
        - authwall / checkpoint / login redirect
    """

    current_url = str(
        page.url
        or ""
    ).strip()

    lowered_url = current_url.lower()

    blocked_fragments = (
        "/404",
        "/login",
        "/checkpoint",
        "/authwall",
        "/challenge",
    )

    if any(
        fragment in lowered_url
        for fragment in blocked_fragments
    ):
        raise RuntimeError(
            "LinkedIn profile page is unavailable or redirected | "
            f"url={current_url}"
        )

    # Read a small amount of visible page text only for state detection.
    try:
        body_text = (
            page.locator("body")
            .inner_text(
                timeout=3_000
            )
            .strip()
            .lower()
        )
    except Exception:
        body_text = ""

    unavailable_markers = (
        "page not found",
        "this page doesn’t exist",
        "this page doesn't exist",
        "profile not found",
        "profile unavailable",
        "this profile is not available",
    )

    if any(
        marker in body_text
        for marker in unavailable_markers
    ):
        raise RuntimeError(
            "LinkedIn profile page is unavailable / 404 | "
            f"url={current_url}"
        )


def scroll_profile_to_bottom(
    page: Page,
) -> None:
    """
    LinkedIn có thể scroll trong một internal container
    thay vì document/window.

    Logic được port từ repo linkedin-auto-mass-messeages:
    tìm vertical scroll container có scroll distance lớn nhất,
    rồi scroll container đó xuống cuối.
    """

    page.evaluate(
        """
        () => {
            const elements = Array.from(
                document.querySelectorAll("*")
            );

            const candidates = [];

            for (const element of elements) {
                const style =
                    window.getComputedStyle(element);

                const overflowY =
                    style.overflowY;

                const scrollable =
                    (
                        overflowY === "auto" ||
                        overflowY === "scroll"
                    ) &&
                    element.scrollHeight >
                    element.clientHeight + 200;

                if (!scrollable) {
                    continue;
                }

                candidates.push({
                    element,
                    distance:
                        element.scrollHeight -
                        element.clientHeight
                });
            }

            candidates.sort(
                (a, b) =>
                    b.distance - a.distance
            );

            if (candidates.length > 0) {
                const target =
                    candidates[0].element;

                target.scrollTop =
                    target.scrollHeight;

                target.dispatchEvent(
                    new Event(
                        "scroll",
                        {
                            bubbles: true
                        }
                    )
                );

                return;
            }

            const scrollingElement =
                document.scrollingElement;

            if (scrollingElement) {
                scrollingElement.scrollTop =
                    scrollingElement.scrollHeight;
            }
        }
        """
    )

    page.wait_for_timeout(
        1_500
    )


def find_profile_message_action(
    page: Page,
) -> Locator:
    """
    Tìm profile Message action.

    Repo cũ dùng href semantics:
        recipient=
        interop=msgOverlay

    Không dùng text "Message" chung trên toàn page.
    """

    candidates = page.locator(
        'a[href*="recipient="]'
        '[href*="interop=msgOverlay"]'
    )

    visible_candidates: list[
        Locator
    ] = []

    for index in range(
        candidates.count()
    ):
        candidate = candidates.nth(
            index
        )

        try:
            if not candidate.is_visible():
                continue

            text = (
                candidate
                .inner_text()
                .strip()
            )

            if text != "Message":
                continue

            visible_candidates.append(
                candidate
            )

        except Exception:
            continue

    if not visible_candidates:
        raise RuntimeError(
            "Visible LinkedIn profile Message action "
            "was not found."
        )

    # Repo cũ sort theo Y position.
    # Ở integration mới chưa dùng positional heuristic.
    # Nếu DOM test thực tế cho thấy nhiều candidates,
    # ta sẽ inspect rồi chọn semantic scope chính xác.
    return visible_candidates[0]


def open_message_composer(
    page: Page,
) -> None:
    """
    Open LinkedIn messaging composer từ profile page.
    """

    assert_profile_page_available(
        page
    )

    scroll_profile_to_bottom(
        page
    )

    message_action = (
        find_profile_message_action(
            page
        )
    )

    message_action.click(
        force=True
    )

    page.wait_for_timeout(
        1_500
    )


def find_message_textbox(
    page: Page,
) -> Locator:
    """
    Tìm visible message textbox.

    Đây vẫn là selector gốc của repo cũ.
    Step sau sẽ scope chặt hơn vào đúng messaging overlay
    nếu DOM thực tế cho phép.
    """

    candidates = page.locator(
        '[contenteditable="true"][role="textbox"], '
        '[contenteditable="true"]'
    )

    for index in range(
        candidates.count()
    ):
        candidate = candidates.nth(
            index
        )

        try:
            if candidate.is_visible():
                return candidate

        except Exception:
            continue

    raise RuntimeError(
        "Visible message textbox was not found."
    )


def find_send_button(
    page: Page,
    textbox: Locator,
) -> Locator:
    """
    Ưu tiên tìm Send trong dialog chứa textbox.
    Chỉ fallback global nếu không tìm thấy trong dialog.
    """

    dialog = textbox.locator(
        'xpath=ancestor::*[@role="dialog"][1]'
    )

    if dialog.count() > 0:
        buttons = dialog.get_by_role(
            "button",
            name="Send",
            exact=True,
        )

        for index in range(
            buttons.count()
        ):
            button = buttons.nth(
                index
            )

            try:
                if button.is_visible():
                    return button

            except Exception:
                continue

    buttons = page.get_by_role(
        "button",
        name="Send",
        exact=True,
    )

    for index in range(
        buttons.count()
    ):
        button = buttons.nth(
            index
        )

        try:
            if button.is_visible():
                return button

        except Exception:
            continue

    raise RuntimeError(
        "Visible Send button was not found."
    )


def inspect_message_composer(
    page: Page,
) -> dict[str, bool]:
    """
    Test helper cho integration step 1.

    Nó mở composer và xác nhận:
    - textbox tìm thấy
    - Send button tìm thấy

    KHÔNG fill và KHÔNG click Send.
    """

    open_message_composer(
        page
    )

    textbox = find_message_textbox(
        page
    )

    send_button = find_send_button(
        page,
        textbox,
    )

    return {
        "composer_opened": True,
        "textbox_found": (
            textbox.is_visible()
        ),
        "send_button_found": (
            send_button.is_visible()
        ),
    }
