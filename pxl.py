import json
import logging
import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
CACHE_PATH = Path(f"{TAG}_cache.json")
M3U_FILENAME = "pixelsports.m3u8"
CACHE_EXPIRY = 19_800 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Functions ---

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

async def scrape():
    cached = load_cache()
    if cached:
        log.info(f"Loaded {len(cached)} items from cache.")
        generate_m3u(cached, M3U_FILENAME)
        return

    async with async_playwright() as p:
        # Launch persistent context to mimic a real profile
        user_data_dir = Path("./browser_profile")
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )

        # 1. Hide the webdriver property
        await browser_context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await browser_context.new_page()
        events = {}

        try:
            log.info(f"Navigating to {BASE_URL}...")
            # Random delay before navigation
            await asyncio.sleep(random.uniform(1, 3))
            
            response = await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            
            if response.status == 403:
                log.error("Access Forbidden (403). The site is still blocking us.")
                # Optional: Save a screenshot to see why it blocked
                await page.screenshot(path="blocked.png")
                return

            # Extract content - site returns raw JSON
            raw_text = await page.inner_text("body")
            api_data = json.loads(raw_text)
            
            now = datetime.now(timezone.utc)
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

            if events:
                CACHE_PATH.write_text(json.dumps(events, indent=4))
                generate_m3u(events, M3U_FILENAME)
                log.info(f"Successfully scraped {len(events)} events.")
        
        except Exception as e:
            log.error(f"Scrape failed: {e}")
        finally:
            await browser_context.close()

if __name__ == "__main__":
    asyncio.run(scrape())
