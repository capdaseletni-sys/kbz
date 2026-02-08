import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
M3U_FILENAME = "pixelsports.m3u8"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def generate_m3u(events, filename):
    if not events: 
        log.warning("No events found. M3U not generated.")
        return
    # Add a timestamp so the file content changes every time (ensures GitHub commit)
    m3u_lines = [f"#EXTM3U\n# UPDATED: {datetime.now(timezone.utc).isoformat()}"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    
    Path(filename).write_text("\n".join(m3u_lines), encoding="utf-8")
    log.info(f"Successfully generated {filename} with {len(events)} events.")

async def scrape():
    async with async_playwright() as p:
        # Launch browser with stealth arguments
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox"
        ])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )

        page = await context.new_page()
        
        # Apply Stealth to hide Playwright fingerprints
        await stealth_async(page)

        try:
            log.info(f"Navigating to API: {BASE_URL}")
            # Increase timeout to 60s to allow Cloudflare to settle
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            
            # Wait for the JSON to appear (browsers wrap raw JSON in <pre>)
            try:
                # Try finding <pre> tag first
                element = page.locator("pre")
                await element.wait_for(state="visible", timeout=15000)
                raw_data = await element.inner_text()
            except:
                # Fallback to full body text if <pre> isn't there
                log.warning("Pre tag not found, attempting body text extraction...")
                raw_data = await page.inner_text("body")

            if not raw_data or "<!DOCTYPE" in raw_data:
                log.error("Blocked by Cloudflare or received empty response.")
                return

            api_json = json.loads(raw_data)
            events = {}
            now = datetime.now(timezone.utc)
            
            for event in api_json.get("events", []):
                try:
                    # Clean and parse date
                    clean_date = event["date"].replace(" ", "T")
                    event_dt = datetime.fromisoformat(clean_date).replace(tzinfo=timezone.utc)
                    
                    # Only today's events
                    if event_dt.date() == now.date():
                        event_name = event["match_name"]
                        chan = event.get("channel", {})
                        sport = chan.get("TVCategory", {}).get("name", "Sports")

                        for i in range(1, 4):
                            link = chan.get(f"server{i}URL")
                            if link and str(link).lower() != "null":
                                key = f"[{sport}] {event_name} S{i} ({TAG})"
                                events[key] = {
                                    "url": link, 
                                    "id": "Live.Event.us"
                                }
                except Exception:
                    continue

            generate_m3u(events, M3U_FILENAME)

        except Exception as e:
            log.error(f"Scrape failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
