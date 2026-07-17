from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    sync_playwright,
)
from supabase import Client, create_client

from app.settings import Settings


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


def create_browser_context(
    browser: Browser,
) -> BrowserContext:
    return browser.new_context(
        viewport={
            "width": 1440,
            "height": 1000,
        },
        locale="en-US",
        timezone_id="Asia/Ho_Chi_Minh",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
    )


def probe_linkedin_source(
    settings: Settings,
) -> ScanProbeResult:
    source = get_one_enabled_source(settings)

    if not source:
        raise RuntimeError(
            "No enabled LinkedIn source found in Supabase."
        )

    source_id = int(source["id"])
    linkedin_url = str(source["linkedin_url"])

    print(
        f"Testing source {source_id}: {linkedin_url}"
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
        )

        context = create_browser_context(browser)
        page: Page = context.new_page()

        try:
            page.goto(
                linkedin_url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

            page.wait_for_timeout(5_000)

            final_url = page.url
            page_title = page.title()

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
            browser.close()
