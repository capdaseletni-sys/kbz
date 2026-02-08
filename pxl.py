import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.async_api import async_playwright
import playwright_stealth

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
M3U_FILENAME = "pixelsports.m3u8"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def generate_m3u(events, filename):
    if not events: 
        log.warning("No events found to save.")
        return
    m3u_lines = [f"#EXTM3U\n# UPDATED: {datetime.now(timezone.utc).isoformat()}"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    
    Path(filename).write_text("\n".join(m3u_lines), encoding="utf-8")
    log.info(f"Successfully generated {filename} with {len(events)} events.")

async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Handle stealth versions
        if hasattr(playwright_stealth, "stealth_async"):
            await playwright_stealth.stealth_async(page)
        else:
            await playwright_stealth.stealth(page)

        try:
            log.info(f"Navigating to: {BASE_URL}")
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            
            # Extract content
            try:
                raw_data = await page.locator("pre").inner_text(timeout=10000)
            except:
                raw_data = await page.inner_text("body")

            if not raw_data or "<!DOCTYPE" in raw_data:
                log.error("Failed to get JSON (Blocked by Cloudflare).")
                return

            api_json = json.loads(raw_data)
            events_list = api_json.get("events", [])
            log.info(f"API returned {len(events_list)} total events.")

            events = {}
            now = datetime.now(timezone.utc).date()
            tomorrow = now + timedelta(days=1)
            
            for event in events_list:
                try:
                    # Parse date
                    clean_date = event["date"].replace(" ", "T")
                    event_dt = datetime.fromisoformat(clean_date).date()
                    
                    # BROADENED FILTER: Today and Tomorrow
                    if event_dt == now or event_dt == tomorrow:
                        event_name = event["match_name"]
                        chan = event.get("channel", {})
                        sport = chan.get("TVCategory", {}).get("name", "Sports")

                        for i in range(1, 4):
                            link = chan.get(f"server{i}URL")
                            if link and str(link).lower() != "null":
                                key = f"[{sport}] {event_name} S{i} ({TAG})"
                                events[key] = {"url": link, "id": "Live.Event.us"}
                except Exception as e:
                    continue

            generate_m3u(events, M3U_FILENAME)

        except Exception as e:
            log.error(f"Scrape failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
