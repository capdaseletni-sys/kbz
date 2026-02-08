import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from seleniumbase import Driver

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
CACHE_PATH = Path(f"{TAG}_cache.json")
M3U_FILENAME = "pixelsports.m3u8"
CACHE_EXPIRY = 19_800 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Utility Functions ---

def load_cache():
    if not CACHE_PATH.exists(): return None
    if (time.time() - CACHE_PATH.stat().st_mtime) > CACHE_EXPIRY: return None
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

def scrape():
    # 1. Check Cache
    cached = load_cache()
    if cached:
        log.info(f"Loaded {len(cached)} items from cache.")
        generate_m3u(cached, M3U_FILENAME)
        return

    # 2. Launch Stealth Driver (UC Mode)
    # uc=True is the "Undetected" mode that bypasses 403/Cloudflare
    log.info("Launching stealth browser...")
    driver = Driver(uc=True, headless=True) 
    
    events = {}
    try:
        log.info(f"Navigating to {BASE_URL}...")
        driver.get(BASE_URL)
        
        # Give it a second to resolve any background challenges
        time.sleep(random.uniform(3, 5))

        # 3. Extract JSON
        # SeleniumBase will handle the challenge, then we grab the result
        page_source = driver.get_text("body")
        api_data = json.loads(page_source)
        
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
                            "url": link, 
                            "id": "Live.Event.us", 
                            "timestamp": now.timestamp()
                        }
            except: continue

        if events:
            CACHE_PATH.write_text(json.dumps(events, indent=4))
            generate_m3u(events, M3U_FILENAME)
            log.info(f"Successfully scraped {len(events)} events.")
        else:
            log.warning("No events found in the API response.")

    except Exception as e:
        log.error(f"Failed to bypass or parse: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape()
