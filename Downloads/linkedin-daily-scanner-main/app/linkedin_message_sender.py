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


def _normalise_person_name(
    value: str | None,
) -> str:
    return " ".join(
        str(
            value
            or ""
        )
        .strip()
        .casefold()
        .split()
    )


def _panel_for_textbox(
    textbox: Locator,
) -> Locator:
    """
    Resolve the mini Messaging conversation panel that owns this textbox.

    The panel is identified semantically:
    - it contains the textbox;
    - it also contains a button with svg[data-test-icon="close-small"].
    """

    panel = textbox.locator(
        'xpath=ancestor::*['
        './/button['
        './/*[local-name()="svg" and '
        '@data-test-icon="close-small"]'
        ']'
        '][1]'
    )

    if panel.count() <= 0:
        raise RuntimeError(
            "Messaging panel containing this textbox was not found."
        )

    return panel


def _panel_matches_profile_name(
    panel: Locator,
    expected_profile_name: str,
) -> bool:
    expected = _normalise_person_name(
        expected_profile_name
    )

    if not expected:
        return False

    try:
        panel_text = _normalise_person_name(
            panel.inner_text()
        )
    except Exception:
        return False

    return expected in panel_text


def close_unrelated_message_panels(
    page: Page,
    expected_profile_name: str,
) -> int:
    """
    Close every visible mini Messaging panel that does NOT belong to the
    profile currently being processed.

    Rule:
        current profile name matches panel -> keep it
        anything else               -> close it

    This runs before opening/filling the target composer, preventing an
    old conversation panel from being reused for the next profile.
    """

    expected = _normalise_person_name(
        expected_profile_name
    )

    if not expected:
        raise ValueError(
            "expected_profile_name is required for safe message routing."
        )

    close_buttons = page.locator(
        'button:has(svg[data-test-icon="close-small"])'
    )

    closed_count = 0

    # Snapshot count because clicking X mutates the DOM.
    button_count = close_buttons.count()

    for index in range(
        button_count - 1,
        -1,
        -1,
    ):
        candidate = close_buttons.nth(
            index
        )

        try:
            if not candidate.is_visible():
                continue
        except Exception:
            continue

        # Restrict only to a conversation panel that also owns a visible
        # contenteditable textbox. This avoids unrelated close icons.
        panel = candidate.locator(
            'xpath=ancestor::*['
            './/*[@contenteditable="true" and @role="textbox"]'
            '][1]'
        )

        if panel.count() <= 0:
            continue

        try:
            textboxes = panel.locator(
                '[contenteditable="true"][role="textbox"]'
            )

            has_visible_textbox = False

            for textbox_index in range(
                textboxes.count()
            ):
                try:
                    if textboxes.nth(
                        textbox_index
                    ).is_visible():
                        has_visible_textbox = True
                        break
                except Exception:
                    continue

            if not has_visible_textbox:
                continue
        except Exception:
            continue

        if _panel_matches_profile_name(
            panel,
            expected_profile_name,
        ):
            continue

        try:
            candidate.click(
                timeout=2_000
            )
        except Exception:
            try:
                candidate.click(
                    timeout=2_000,
                    force=True,
                )
            except Exception:
                continue

        closed_count += 1

        page.wait_for_timeout(
            250
        )

    return closed_count


def find_message_textbox(
    page: Page,
    *,
    expected_profile_name: str | None = None,
) -> Locator:
    """
    Find the visible textbox for the CURRENT target profile.

    When expected_profile_name is provided, this function refuses to use
    any visible textbox whose Messaging panel does not contain that name.
    This prevents a stale conversation from receiving the next message.
    """

    candidates = page.locator(
        '[contenteditable="true"][role="textbox"], '
        '[contenteditable="true"]'
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
        except Exception:
            continue

        if expected_profile_name:
            try:
                panel = _panel_for_textbox(
                    candidate
                )
            except Exception:
                continue

            if not _panel_matches_profile_name(
                panel,
                expected_profile_name,
            ):
                continue

        visible_candidates.append(
            candidate
        )

    if visible_candidates:
        return visible_candidates[0]

    if expected_profile_name:
        raise RuntimeError(
            "Visible message textbox for current profile was not found | "
            f"expected_profile_name={expected_profile_name}"
        )

    raise RuntimeError(
        "Visible message textbox was not found."
    )


def find_send_button(
    page: Page,
    textbox: Locator,
) -> Locator:
    """
    Find Send only inside the Messaging panel that owns this textbox.

    This prevents a stale conversation panel from donating its Send
    button when multiple mini Messaging panels are open.
    """

    try:
        panel = _panel_for_textbox(
            textbox
        )

        buttons = panel.get_by_role(
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

    except Exception:
        pass

    raise RuntimeError(
        "Visible Send button was not found inside "
        "the current profile Messaging panel."
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


def find_message_panel(
    textbox: Locator,
) -> Locator:
    return _panel_for_textbox(
        textbox
    )


def close_message_composer(
    page: Page,
    textbox: Locator,
) -> bool:
    """
    Click the close-small X inside the SAME Messaging panel that owns
    the textbox used for the current message.

    LinkedIn can keep or recycle the panel DOM after the click, so DOM
    disappearance is NOT used as the success condition.

    Success condition:
        the correct close-small button was found and clicked.

    Safety for the next target is handled separately by:
        close_unrelated_message_panels()
        + recipient-name guarded textbox selection.
    """

    panel = find_message_panel(
        textbox
    )

    close_buttons = panel.locator(
        'button:has(svg[data-test-icon="close-small"])'
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
            "Message was sent, but the close-small button "
            "was not found inside the current Messaging panel."
        )

    try:
        close_button.click(
            timeout=2_500
        )

    except Exception:
        close_button.click(
            timeout=2_500,
            force=True,
        )

    # Give LinkedIn a short moment to process the UI action.
    # Do not require the panel node to detach or become hidden.
    page.wait_for_timeout(
        350
    )

    return True


def click_discard_confirmation(
    page: Page,
    *,
    timeout_ms: int = 2_000,
) -> bool:
    """
    Click LinkedIn's visible "Discard" confirmation after closing a
    Messaging composer.

    This is cleanup only:
    - if the confirmation does not appear, return False;
    - if it appears, click the exact visible Discard button;
    - do not change the already-successful Send result.
    """

    # Give the confirmation a short chance to appear after the X click.
    page.wait_for_timeout(
        300
    )

    deadline = (
        page.evaluate("Date.now()")
        + timeout_ms
    )

    while (
        page.evaluate("Date.now()")
        < deadline
    ):
        # Prefer a visible dialog scope so we do not click an unrelated
        # "Discard" action somewhere else on the page.
        dialogs = page.locator(
            '[role="dialog"]'
        )

        for dialog_index in range(
            dialogs.count()
        ):
            dialog = dialogs.nth(
                dialog_index
            )

            try:
                if not dialog.is_visible():
                    continue
            except Exception:
                continue

            buttons = dialog.get_by_role(
                "button",
                name="Discard",
                exact=True,
            )

            for button_index in range(
                buttons.count()
            ):
                button = buttons.nth(
                    button_index
                )

                try:
                    if not button.is_visible():
                        continue

                    try:
                        button.click(
                            timeout=1_500
                        )
                    except Exception:
                        button.click(
                            timeout=1_500,
                            force=True,
                        )

                    page.wait_for_timeout(
                        300
                    )

                    return True

                except Exception:
                    continue

        page.wait_for_timeout(
            150
        )

    return False


def send_message_once(
    page: Page,
    message: str,
    *,
    expected_profile_name: str,
) -> dict[str, bool | int]:
    """
    Send ONE message only to the profile currently being processed.

    Safe routing flow:
        current LinkedIn profile
        -> close all old Messaging panels whose recipient name differs
        -> open current profile composer
        -> find textbox whose panel contains expected_profile_name
        -> fill
        -> Send
        -> close current panel

    Send click remains the success boundary.
    """

    closed_unrelated_before_send = (
        close_unrelated_message_panels(
            page,
            expected_profile_name,
        )
    )

    open_message_composer(
        page
    )

    # LinkedIn can keep old panels alive after opening a new composer.
    # Clean once more, then select ONLY the textbox for this profile.
    closed_unrelated_after_open = (
        close_unrelated_message_panels(
            page,
            expected_profile_name,
        )
    )

    textbox = find_message_textbox(
        page,
        expected_profile_name=(
            expected_profile_name
        ),
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

    # Give LinkedIn time to commit the sent message and clear the composer
    # state before closing the mini-chat. Closing too quickly can trigger
    # LinkedIn's "Discard message?" confirmation.
    page.wait_for_timeout(
        1800
    )

    composer_closed = close_message_composer(
        page,
        textbox,
    )

    # LinkedIn can occasionally show a "Discard message?" confirmation
    # even after Send succeeded. Clear it before moving to the next profile.
    discard_clicked = click_discard_confirmation(
        page
    )

    return {
        "composer_opened": True,
        "textbox_found": True,
        "message_filled": True,
        "send_button_found": True,
        "send_clicked": True,
        "sent_verified": True,
        "composer_closed": composer_closed,
        "discard_clicked": discard_clicked,
        "closed_unrelated_panels": (
            closed_unrelated_before_send
            + closed_unrelated_after_open
        ),
    }

