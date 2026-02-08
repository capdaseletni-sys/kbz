import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import Browser, Page

# --------------------------------------------------
# Config
# --------------------------------------------------

BASE_URL = "https://pixelsport.tv/backend/livetv/events"
TAG = "PIXEL"
M3U_FILE = Path("pixelsports.m3u8")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pixelsport")

urls: dict[str, dict[str, str | float]] = {}

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def write_m3u(events: dict[str, dict[str, str | float]]) -> None:
    lines = ["#EXTM3U"]

    for name, data in events.items():
        lines.append(
            '#EXTINF:-1 '
            f'tvg-id="{data["id"]}" '
            f'tvg-logo="{data["logo"]}",'
            f'{name}'
        )
        lines.append(data["url"])

    M3U_FILE.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------
# Scraping
# --------------------------------------------------

async def get_api_data(page: Page) -> dict:
    try:
        await page.goto(
            BASE_URL,
            wait_until="domcontentloaded",
            timeout=10_000,
        )

        raw_json = await page.locator("pre").inner_text(timeout=5_000)
        return json.loads(raw_json)

    except Exception as e:
        log.error(f"Failed to fetch API: {e}")
        return {}


async def get_events(page: Page) -> dict[str, dict[str, str | float]]:
    api_data = await get_api_data(page)
    today = now_utc().date()

    events = {}

    for event in api_data.get("events", []):
        try:
            event_dt = datetime.fromisoformat(
                event["date"].replace("Z", "+00:00")
            )
        except Exception:
            continue

        if event_dt.date() != today:
            continue

        event_name = event["match_name"]
        channel = event["channel"]
        sport = channel["TVCategory"]["name"]

        for i in range(1, 4):
            stream_link = channel.get(f"server{i}URL")
            if not stream_link or stream_link == "null":
                continue

            key = f"[{sport}] {event_name} {i} ({TAG})"

            events[key] = {
                "url": stream_link,
                "logo": "",                  # no leagues util
                "base": "https://pixelsport.tv",
                "timestamp": now_utc().timestamp(),
                "id": "Live.Event",          # safe default
            }

    return events


async def scrape(browser: Browser) -> None:
    log.info(f'Scraping "{BASE_URL}"')

    context = await browser.new_context()
    page = await context.new_page()

    try:
        events = await get_events(page)
    finally:
        await context.close()

    if not events:
        log.warning("No events found")
        return

    urls.clear()
    urls.update(events)

    write_m3u(urls)

    log.info(f"Wrote {len(urls)} event(s) to {M3U_FILE}")
