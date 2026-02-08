import json
import logging
import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

# --- Configuration ---
TAG = "PIXEL"
SITE_URL = "https://pixelsport.tv/" # Main site for cookies
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
CACHE_PATH = Path(f"{TAG}_cache.json")
M3U_FILENAME = "pixelsports.m3u8"
CACHE_EXPIRY = 19_800 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Logic ---

def generate_m3u(events, filename):
    if not events: return
    m3u_lines = ["#EXTM3U"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" tvg-logo="" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

async def scrape():
    async with async_playwright() as p:
        # 1. Start with a real-looking browser
        browser = await p.chromium.launch(headless=True)
        
        # Use a high-quality User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": SITE_URL
            }
        )

        page = await context.new_page()
        events = {}

        try:
            # 2. THE HANDSHAKE: Visit the homepage first to collect session cookies/tokens
            log.info(f"Performing handshake with {SITE_URL}...")
            await page.goto(SITE_URL, wait_until="networkidle")
            await asyncio.sleep(random.uniform(2, 4)) # Act human

            # 3. THE REQUEST: Now try the API while carrying those cookies
            log.info(f"Fetching API data from {BASE_URL}...")
            
            # Instead of goto, we use page.evaluate to fetch via the browser's internal fetch
            # This ensures all cookies, headers, and fingerprints are 100% correct.
            api_json = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{BASE_URL}');
                    return await response.json();
                }}
            """)

            now = datetime.now(timezone.utc)
            for event in api_json.get("events", []):
                try:
                    # Fix date format for standard ISO parsing
                    clean_date = event["date"].replace(" ", "T")
                    event_dt = datetime.fromisoformat(clean_date).replace(tzinfo=timezone.utc)
                    
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
                except Exception: continue

            if events:
                Path(M3U_FILENAME).write_text("") # Clear old file
                generate_m3u(events, M3U_FILENAME)
                log.info(f"Success! Generated {M3U_FILENAME} with {len(events)} events.")
            else:
                log.warning("API returned 0 events for today.")

        except Exception as e:
            log.error(f"Handshake failed: {e}")
            # If the site uses Cloudflare, it might need 'headless: False' once locally.
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
