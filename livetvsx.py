import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path

import feedparser
import httpx
from playwright.async_api import Browser, Page, async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("LIVETVSX")

TAG = "LIVETVSX"
CACHE_PATH = Path("cache_urls.json")
BASE_URL = "https://cdn.livetv861.me/rss/upcoming_en.xml"
VALID_SPORTS = {"Football", "Basketball", "Ice Hockey"}

def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=4)

async def process_event(url: str, page: Page) -> str | None:
    captured_url = []
    
    # Listen for the manifest file in the network traffic
    async def intercept_request(request):
        if ".m3u8" in request.url and "index" in request.url:
            captured_url.append(request.url)

    page.on("request", intercept_request)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

        # Select valid stream links
        buttons = await page.query_selector_all(".lnktbj a[href*='webplayer']")
        labels = await page.eval_on_selector_all(
            ".lnktyt span",
            "elements => elements.map(el => el.textContent.trim().toLowerCase())",
        )

        target_href = None
        for btn, label in zip(buttons, labels):
            if any(x in label for x in ["web", "youtube", "browser"]):
                continue
            target_href = await btn.get_attribute("href")
            if target_href: break

        if not target_href:
            return None

        final_url = target_href if target_href.startswith("http") else f"https:{target_href}"
        await page.goto(final_url, wait_until="domcontentloaded", timeout=10000)

        # Polling for the captured M3U8
        for _ in range(20): 
            if captured_url:
                return captured_url[0]
            await asyncio.sleep(0.5)

    except Exception as e:
        log.debug(f"Process error: {e}")
    return None

async def scrape(browser: Browser):
    cached_data = load_cache()
    
    # Fetch RSS Feed
    async with httpx.AsyncClient() as client:
        r = await client.get(BASE_URL)
        feed = feedparser.parse(r.text)

    now = datetime.now(timezone.utc)
    start_window = (now - timedelta(hours=1)).timestamp()
    end_window = (now + timedelta(minutes=10)).timestamp()

    current_playlist_entries = []

    for entry in feed.entries:
        title = entry.get("title")
        link = entry.get("link")
        summary = entry.get("summary", "")
        
        # Parse sport and check validity
        parts = summary.split(".", 1)
        sport = parts[0]
        if sport not in VALID_SPORTS:
            continue

        # Parse time
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        event_ts = dt.timestamp()

        if not (start_window <= event_ts <= end_window):
            continue

        # Check cache first
        if link in cached_data and (now.timestamp() - cached_data[link]['cached_at'] < 10800):
            m3u8_url = cached_data[link]['url']
        else:
            log.info(f"Scraping: {title}")
            page = await browser.new_page()
            m3u8_url = await process_event(link, page)
            await page.close()
            
            if m3u8_url:
                cached_data[link] = {"url": m3u8_url, "cached_at": now.timestamp()}

        if m3u8_url:
            current_playlist_entries.append(f'#EXTINF:-1 group-title="livetvsx", {title}\n{m3u8_url}')

    # Save Cache
    save_cache(cached_data)

    # Save Playlist to livetvsx.m3u8
    with open("livetvsx.m3u8", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n" + "\n".join(current_playlist_entries))
    
    log.info(f"Playlist updated: livetvsx.m3u8 ({len(current_playlist_entries)} streams)")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await scrape(browser)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
