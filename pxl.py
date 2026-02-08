import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import stealth

# --- Configuration ---
TAG = "PIXEL"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
M3U_FILENAME = "pixelsports.m3u8"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def generate_m3u(events, filename):
    if not events: return
    m3u_lines = ["#EXTM3U"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    Path(filename).write_text("\n".join(m3u_lines), encoding="utf-8")

async def scrape():
    async with async_playwright() as p:
        # 1. Launch with specific arguments to look less like a bot
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox"
        ])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()
        
        # 2. Apply Stealth
        await stealth(page)

        try:
            log.info(f"Navigating to API...")
            # Navigate and wait longer for Cloudflare to settle
            await page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            
            # 3. Try to find the JSON. 
            # If Cloudflare is there, 'pre' won't exist.
            try:
                # Wait up to 15 seconds for the JSON container to appear
                pre_element = page.locator("pre")
                await pre_element.wait_for(state="visible", timeout=15000)
                raw_json = await pre_element.inner_text()
            except:
                # If we fail, it might be because the browser rendered it as plain text in the body
                log.warning("Pre tag not found, trying body text...")
                raw_json = await page.inner_text("body")

            # 4. Parse JSON
            api_json = json.loads(raw_json)
            events = {}
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
                            events[key] = {"url": link, "id": "Live.Event.us"}
                except: continue

            if events:
                generate_m3u(events, M3U_FILENAME)
                log.info(f"Success! Generated {len(events)} events.")
            else:
                log.error("API loaded but no events found for today.")

        except Exception as e:
            # Log the page content on failure to see if it's a Cloudflare challenge
            content = await page.content()
            if "cloudflare" in content.lower() or "challenge-form" in content.lower():
                log.error("Blocked by Cloudflare challenge page.")
            else:
                log.error(f"Scrape failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
