import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
CACHE_PATH = Path(f"{TAG}_cache.json")
M3U_FILENAME = "pixelsports.m3u8"
CACHE_EXPIRY = 19_800  # 5.5 hours

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Global storage for URLs
urls: dict[str, dict[str, str | float]] = {}

# --- Utility Functions ---

def load_cache() -> dict | None:
    """Loads data from local JSON if it hasn't expired."""
    if not CACHE_PATH.exists():
        return None
    
    stats = CACHE_PATH.stat()
    if (datetime.now().timestamp() - stats.st_mtime) > CACHE_EXPIRY:
        log.info("Cache expired.")
        return None
        
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception as e:
        log.error(f"Failed to read cache: {e}")
        return None

def save_cache(data: dict):
    """Saves the scraped data to a local JSON file."""
    CACHE_PATH.write_text(json.dumps(data, indent=4))

def generate_m3u(events: dict, filename: str):
    """Converts the events dictionary into an M3U8 playlist file."""
    if not events:
        log.warning("No events found; M3U not generated.")
        return

    m3u_lines = ["#EXTM3U"]
    for name, data in events.items():
        tvg_id = data.get("id", "Live.Event.us")
        logo = data.get("logo", "")
        url = data.get("url")
        # Extract sport for group-title
        sport_match = name.split(']')[0].replace('[', '') if ']' in name else "Sports"

        line = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{sport_match}",{name}'
        m3u_lines.append(line)
        m3u_lines.append(url)

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    log.info(f"Playlist generated: {filename}")

# --- Core Logic ---

async def get_api_data(page: Page) -> dict:
    """Fetches JSON data directly via Playwright's request context."""
    try:
        response = await page.request.get(BASE_URL, timeout=10_000)
        if response.ok:
            return await response.json()
        log.error(f"API Error: {response.status}")
    except Exception as e:
        log.error(f"Request failed: {e}")
    return {}

async def get_events(page: Page) -> dict:
    """Parses the raw API data into a structured event dictionary."""
    now = datetime.now(timezone.utc)
    api_data = await get_api_data(page)
    events = {}

    for event in api_data.get("events", []):
        try:
            # Parse '2026-02-08 15:30:00' format (common in sports APIs)
            event_dt = datetime.fromisoformat(event["date"].replace(" ", "T"))
            
            # Only include today's events
            if event_dt.date() != now.date():
                continue

            event_name = event["match_name"]
            channel_info = event.get("channel", {})
            sport = channel_info.get("TVCategory", {}).get("name", "Sports")

            # Check servers 1 through 3
            for i in range(1, 4):
                stream_link = channel_info.get(f"server{i}URL")

                if stream_link and str(stream_link).lower() != "null":
                    key = f"[{sport}] {event_name} S{i} ({TAG})"
                    
                    events[key] = {
                        "url": stream_link,
                        "logo": "", 
                        "base": "https://pixelsport.tv",
                        "timestamp": now.timestamp(),
                        "id": "Live.Event.us",
                    }
        except (KeyError, ValueError):
            continue

    return events

async def scrape(browser: Browser) -> None:
    """Main execution flow for scraping and file generation."""
    global urls
    
    cached = load_cache()
    if cached:
        urls.update(cached)
        log.info(f"Loaded {len(urls)} event(s) from cache")
        generate_m3u(urls, M3U_FILENAME)
        return

    log.info(f'Scraping fresh data from "{BASE_URL}"')
    context = await browser.new_context()
    page = await context.new_page()
    
    try:
        scraped_events = await get_events(page)
        if scraped_events:
            urls.update(scraped_events)
            save_cache(urls)
            generate_m3u(urls, M3U_FILENAME)
            log.info(f"Success! {len(urls)} events processed.")
        else:
            log.warning("No active events found on the API today.")
    finally:
        await context.close()

# --- Entry Point ---

async def main():
    async with async_playwright() as p:
        # Launching headless browser
        browser = await p.chromium.launch(headless=True)
        await scrape(browser)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
