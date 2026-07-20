from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page, sync_playwright
from supabase import Client, create_client

from app.settings import Settings


LINKEDIN_PROFILE_DIR = Path("linkedin_browser_profile")


@dataclass
class ScanProbeResult:
    source_id: int
    linkedin_url: str
    final_url: str
    page_title: str
    body_preview: str


def create_supabase_client(settings: Settings) -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key,
    )


def get_one_enabled_source(
    settings: Settings,
) -> dict | None:
    client = create_supabase_client(settings)

    response = (
        client.table("linkedin_sources")
        .select("id,name,linkedin_url,source_type")
        .eq("enabled", True)
        .order("last_scanned_at", desc=False)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]

def get_enabled_source_by_id(
    settings: Settings,
    source_id: int,
) -> dict | None:
    client = create_supabase_client(settings)

    response = (
        client.table("linkedin_sources")
        .select("id,name,linkedin_url,source_type")
        .eq("id", source_id)
        .eq("enabled", True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]

def is_blocked_linkedin_url(url: str) -> bool:
    blocked_paths = (
        "/login",
        "/authwall",
        "/checkpoint",
    )

    return any(
        path in url.lower()
        for path in blocked_paths
    )


def accept_cookie_banner(page: Page) -> bool:
    possible_buttons = (
        "button:has-text('Accept cookies')",
        "button:has-text('Accept all')",
        "button:has-text('Allow all cookies')",
        "button:has-text('Agree')",
        "button[action-type='ACCEPT']",
    )

    for selector in possible_buttons:
        try:
            button = page.locator(selector).first

            if button.is_visible(timeout=1_000):
                button.click(timeout=3_000)
                page.wait_for_timeout(1_000)

                print("Accepted LinkedIn cookie banner.")
                return True

        except Exception:
            continue

    return False


def probe_linkedin_source(
    settings: Settings,
) -> ScanProbeResult:
    source = get_one_enabled_source(settings)

    if not source:
        raise RuntimeError(
            "No enabled LinkedIn source found in Supabase."
        )

    if not LINKEDIN_PROFILE_DIR.exists():
        raise RuntimeError(
            "LinkedIn browser profile does not exist. "
            "Run create_linkedin_session.py first."
        )

    source_id = int(source["id"])
    linkedin_url = str(source["linkedin_url"])

    print(
        f"Testing source {source_id}: {linkedin_url}"
    )

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(
                LINKEDIN_PROFILE_DIR.resolve()
            ),
            headless=False,
            viewport={
                "width": 1440,
                "height": 1000,
            },
            locale="en-US",
            timezone_id="Asia/Ho_Chi_Minh",
        )

        page: Page = (
            context.pages[0]
            if context.pages
            else context.new_page()
        )

        try:
            page.goto(
                linkedin_url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            page.wait_for_timeout(4_000)

            accept_cookie_banner(page)

            page.wait_for_timeout(2_000)

            final_url = page.url
            page_title = page.title()

            if is_blocked_linkedin_url(final_url):
                raise RuntimeError(
                    "LINKEDIN_SESSION_BLOCKED: "
                    f"LinkedIn redirected to {final_url}"
                )

            body_text = page.locator("body").inner_text(
                timeout=15_000
            )

            body_preview = " ".join(
                body_text.split()
            )[:500]

            return ScanProbeResult(
                source_id=source_id,
                linkedin_url=linkedin_url,
                final_url=final_url,
                page_title=page_title,
                body_preview=body_preview,
            )

        finally:
            context.close()
