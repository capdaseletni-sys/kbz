import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

# --------------------------------------------------
# Config
# --------------------------------------------------

BASE_URL = "https://pixelsport.tv/backend/livetv/events"
M3U_FILE = Path("pixelsports.m3u8")
TAG = "PIXEL"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://pixelsport.tv/",
    "Origin": "https://pixelsport.tv",
}

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pixelsport")

# --------------------------------------------------
# Helpers
# --------------------------------------------------

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


# --------------------------------------------------
# API
# --------------------------------------------------

async def get_events() -> dict[str, dict]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0) as client:
        r = await client.get(BASE_URL)
        r.raise_for_status()
        api_data = r.json()

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

    return events


# --------------------------------------------------
# Main
# --------------------------------------------------

async def main():
    log.info("Fetching PixelSport events...")
    events = await get_events()

    if not events:
        log.warning("No events found")
        return

    write_m3u(events)
    log.info(f"Saved {len(events)} streams to {M3U_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
