import json
import logging
import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
CACHE_PATH = Path(f"{TAG}_cache.json")
M3U_FILENAME = "pixelsports.m3u8"
CACHE_EXPIRY = 19_800 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

urls: dict[str, dict[str, str | float]] = {}

# --- Helper Functions ---

def load_cache():
    if not CACHE_PATH.exists(): return None
    if (datetime.now().timestamp() - CACHE_PATH.stat().st_mtime) > CACHE_EXPIRY: return None
    try: return json.loads(CACHE_PATH.read_text())
    except: return None

def generate_m3u(events, filename):
    if not events: return
    m3u_lines = ["#EXTM3U"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" tvg-logo="" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))
    log.info(f"Playlist generated: {filename}")

# --- Scraper Logic ---

async def get_events(page: Page) -> dict:
    now = datetime.now(timezone.utc)
    events = {}

    try:
        # 1. Navigate to the URL instead of using raw request
        log.info(f"Navigating to {BASE_URL}...")
        response = await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
        
        if response.status == 403:
            log.error("Access Forbidden (403). The site is blocking the automated browser.")
            return {}

        # 2. Extract JSON from the page body (browsers often wrap JSON in <pre> tags)
        content = await page.content()
        # Clean the content to find the JSON string
        raw_text = await page.inner_text("body")
        api_data = json.loads(raw_text)

        for event in api_data.get("events", []):
            try:
                event_dt = datetime.fromisoformat(event["date"].replace(" ", "T"))
                if event_dt.date() != now.date(): continue

                event_name = event["match_name"]
                chan = event.get("channel", {})
                sport = chan.get("TVCategory", {}).get("name", "Sports")

                for i in range(1, 4):
                    link = chan.get(f"server{i}URL")
                    if link and str(link).lower() != "null":
                        key = f"[{sport}] {event_name} S{i} ({TAG})"
                        events[key] = {
                            "url": link, "id": "Live.Event.us", "timestamp": now.timestamp()
                        }
            except: continue
    except Exception as e:
        log.error(f"Parsing error: {e}")

    return events

async def scrape(browser: Browser):
    global urls
    cached = load_cache()
    if cached:
        urls.update(cached)
        generate_m3u(urls, M3U_FILENAME)
        log.info(f"Loaded {len(urls)} items from cache.")
        return

    # Use a realistic User-Agent and disable the automation flag
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    
    # Anti-detection script: Remove the 'webdriver' property
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = await context.new_page()
    try:
        scraped_events = await get_events(page)
        if scraped_events:
            urls.update(scraped_events)
            CACHE_PATH.write_text(json.dumps(urls, indent=4))
            generate_m3u(urls, M3U_FILENAME)
    finally:
        await context.close()

async def main():
    async with async_playwright() as p:
        # Headless=False can sometimes help bypass 403s if Headless is detected
        browser = await p.chromium.launch(headless=True)
        await scrape(browser)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
