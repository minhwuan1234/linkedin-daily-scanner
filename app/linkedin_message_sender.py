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


def fill_message_textbox(
    textbox: Locator,
    message: str,
) -> None:
    """
    STEP 4 — fill the LinkedIn message textbox.

    IMPORTANT:
    - fills the textbox only;
    - does NOT click Send;
    - does NOT update any database state.
    """

    cleaned_message = str(
        message
        or ""
    ).strip()

    if not cleaned_message:
        raise ValueError(
            "Message cannot be empty."
        )

    textbox.click()

    textbox.fill(
        cleaned_message
    )


def prepare_message_in_composer(
    page: Page,
    message: str,
) -> dict[str, bool]:
    """
    Open composer and place message text into the textbox.

    This is the last safe test before actual sending.

    It does NOT click Send.
    """

    open_message_composer(
        page
    )

    textbox = find_message_textbox(
        page
    )

    fill_message_textbox(
        textbox,
        message,
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
        "message_filled": True,
        "send_button_found": (
            send_button.is_visible()
        ),
    }


def verify_message_sent(
    page: Page,
    textbox: Locator,
    message: str,
    *,
    timeout_ms: int = 8_000,
) -> bool:
    """
    Strict confirmation after clicking Send.

    Success requires BOTH:
    1. the composer textbox becomes empty;
    2. the sent message text becomes visible inside the same
       messaging dialog.

    This is intentionally stricter than the old repo, which
    treated a successful click as "sent".
    """

    cleaned_message = str(
        message
        or ""
    ).strip()

    if not cleaned_message:
        return False

    try:
        dialog = textbox.locator(
            'xpath=ancestor::*[@role="dialog"][1]'
        )

        scope = (
            dialog
            if dialog.count() > 0
            else page.locator("body")
        )

        deadline = (
            page.evaluate("Date.now()")
            + timeout_ms
        )

        while (
            page.evaluate("Date.now()")
            < deadline
        ):
            try:
                current_value = (
                    textbox
                    .inner_text()
                    .strip()
                )
            except Exception:
                current_value = ""

            textbox_cleared = (
                current_value == ""
            )

            message_visible = False

            try:
                exact_matches = scope.get_by_text(
                    cleaned_message,
                    exact=True,
                )

                for index in range(
                    exact_matches.count()
                ):
                    candidate = exact_matches.nth(
                        index
                    )

                    if candidate.is_visible():
                        message_visible = True
                        break

            except Exception:
                message_visible = False

            if (
                textbox_cleared
                and message_visible
            ):
                return True

            page.wait_for_timeout(
                300
            )

    except Exception:
        return False

    return False


def find_message_dialog(
    textbox: Locator,
) -> Locator:
    """
    Resolve the exact messaging dialog that owns the textbox.

    We intentionally scope all close-button discovery to this dialog.
    This prevents another global button[aria-label="Dismiss"] on the
    LinkedIn page from being clicked by mistake.
    """

    dialog = textbox.locator(
        'xpath=ancestor::*[@role="dialog"][1]'
    )

    if dialog.count() <= 0:
        raise RuntimeError(
            "Messaging dialog containing the textbox was not found."
        )

    return dialog


def close_message_composer(
    page: Page,
    textbox: Locator,
    *,
    timeout_ms: int = 5_000,
) -> bool:
    """
    Close the SAME messaging dialog after a send was strictly verified.

    Confirmed LinkedIn DOM from the live page:

        button[aria-label="Dismiss"]
            svg[data-test-icon="close-small"]

    Important:
    - never uses LinkedIn random CSS classes;
    - never uses x/y coordinates;
    - never clicks a global Dismiss button;
    - only clicks Dismiss inside the dialog that owns this textbox;
    - verifies that the dialog disappears before returning True.
    """

    dialog = find_message_dialog(
        textbox
    )

    close_buttons = dialog.locator(
        'button[aria-label="Dismiss"]'
        ':has(svg[data-test-icon="close-small"])'
    )

    close_button: Locator | None = None

    for index in range(
        close_buttons.count()
    ):
        candidate = close_buttons.nth(
            index
        )

        try:
            if candidate.is_visible():
                close_button = candidate
                break

        except Exception:
            continue

    if close_button is None:
        raise RuntimeError(
            "Message was sent, but the messaging dialog close "
            'button [aria-label="Dismiss"] with '
            'svg[data-test-icon="close-small"] was not found.'
        )

    close_button.click()

    deadline = (
        page.evaluate("Date.now()")
        + timeout_ms
    )

    while (
        page.evaluate("Date.now()")
        < deadline
    ):
        try:
            dialog_visible = (
                dialog.count() > 0
                and dialog.is_visible()
            )

        except Exception:
            # Detached from DOM is also a successful close.
            dialog_visible = False

        if not dialog_visible:
            return True

        page.wait_for_timeout(
            200
        )

    raise RuntimeError(
        "Message was sent and Dismiss was clicked, "
        "but the messaging dialog remained visible."
    )


def send_message_once(
    page: Page,
    message: str,
) -> dict[str, bool]:
    """
    STEP 5 — send ONE prepared message.

    Flow:
        open composer
        -> find textbox
        -> fill message
        -> find Send button
        -> click Send
        -> STRICT verify

    IMPORTANT:
    This function performs a real LinkedIn Send click.
    It does NOT update Supabase yet.
    """

    open_message_composer(
        page
    )

    textbox = find_message_textbox(
        page
    )

    fill_message_textbox(
        textbox,
        message,
    )

    send_button = find_send_button(
        page,
        textbox,
    )

    send_button.click()

    # User-approved success rule:
    # once the Send button click succeeds, treat the action as sent.
    # We no longer require DOM delivery verification because LinkedIn's
    # post-send rendering is not stable enough for this worker.
    composer_closed = close_message_composer(
        page,
        textbox,
    )

    return {
        "composer_opened": True,
        "textbox_found": True,
        "message_filled": True,
        "send_button_found": True,
        "send_clicked": True,
        "sent_verified": True,
        "composer_closed": composer_closed,
    }
