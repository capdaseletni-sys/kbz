import json
import logging
import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

# --- Configuration ---
TAG = "PIXEL"
SITE_URL = "https://pixelsport.tv/" 
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
M3U_FILENAME = "pixelsports.m3u8"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

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
        browser = await p.chromium.launch(headless=True)
        
        # High-quality headers to look less like a bot
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()
        events = {}

        try:
            log.info(f"Performing handshake with {SITE_URL}...")
            # Navigate and wait for the page to actually load to solve challenges
            await page.goto(SITE_URL, wait_until="networkidle")
            await asyncio.sleep(5) # Give Cloudflare extra time to settle

            log.info(f"Fetching API data from {BASE_URL}...")
            
            # We use page.evaluate but wrap it in a try/catch to see the raw text if it fails
            raw_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{BASE_URL}');
                    return await response.text(); 
                }}
            """)

            if raw_data.strip().startswith("<!DOCTYPE"):
                log.error("Received HTML instead of JSON. We are likely blocked by Cloudflare.")
                return

            api_json = json.loads(raw_data)
            now = datetime.now(timezone.utc)
            
            for event in api_json.get("events", []):
                try:
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
                generate_m3u(events, M3U_FILENAME)
                log.info(f"Success! Generated {M3U_FILENAME} with {len(events)} events.")
            else:
                log.warning("API returned 0 events for today.")

        except Exception as e:
            log.error(f"Scrape failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
     asyncio.run(scrape())
