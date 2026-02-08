import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright, Page

LIVE_URL = "https://pixelsport.tv/livetv"
M3U_FILE = Path("pixelsports.m3u8")
TAG = "PIXEL"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pixelsport")

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def write_m3u(events: dict[str, dict]) -> None:
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

async def get_events(page: Page) -> dict[str, dict]:
    events = {}

    # Listen for network responses
    async def handle_response(response):
        if "backend/livetv/events" in response.url and response.status == 200:
            try:
                data = await response.json()
                today = now_utc().date()
                for event in data.get("events", []):
                    try:
                        event_dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                    except Exception:
                        continue
                    if event_dt.date() != today:
                        continue

                    event_name = event.get("match_name", "Live Event")
                    channel = event.get("channel", {})
                    sport = channel.get("TVCategory", {}).get("name", "Sport")

                    for i in range(1, 4):
                        stream = channel.get(f"server{i}URL")
                        if not stream or stream == "null":
                            continue

                        key = f"[{sport}] {event_name} {i} ({TAG})"
                        events[key] = {
                            "url": stream,
                            "logo": "",
                            "id": "Live.Event",
                            "timestamp": now_utc().timestamp(),
                        }
            except Exception as e:
                log.warning(f"Failed parsing events: {e}")

    page.on("response", handle_response)
    await page.goto(LIVE_URL, wait_until="networkidle", timeout=30000)
    # wait a bit for XHR to complete
    await asyncio.sleep(5)
    return events

async def main():
    log.info("Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        log.info("Fetching PixelSport events...")
        events = await get_events(page)

        if events:
            write_m3u(events)
            log.info(f"Saved {len(events)} streams to {M3U_FILE}")
        else:
            log.warning("No events found")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
