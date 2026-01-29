import asyncio
import logging
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone

import httpx
from playwright.async_api import async_playwright
from selectolax.parser import HTMLParser

# Setup basic logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("STRMHUB")

TAG = "STRMHUB"
BASE_URL = "https://streamhub.pro/"

CATEGORIES = {
    "Soccer": "sport_68c02a4464a38",
    "American Football": "sport_68c02a4465113",
    "Basketball": "sport_68c02a4466011",
    "Cricket": "sport_68c02a44669f3",
    "Hockey": "sport_68c02a4466f56",
    "MMA": "sport_68c02a44674e9",
    "Racing": "sport_68c02a4467a48",
    "Tennis": "sport_68c02a4468cf7",
}

async def refresh_html_cache(date_str, sport_id):
    events = {}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                urljoin(BASE_URL, f"events/{date_str}"),
                params={"sport_id": sport_id},
                timeout=10
            )
            if response.status_code != 200:
                return events
            
            soup = HTMLParser(response.text)
            for section in soup.css(".events-section"):
                sport_node = section.css_first(".section-titlte")
                if not sport_node: continue
                
                sport = sport_node.text(strip=True)
                
                for event in section.css(".section-event"):
                    event_name = "Live Event"
                    if teams := event.css_first(".event-competitors"):
                        parts = teams.text(strip=True).split("vs.")
                        if len(parts) == 2:
                            home, away = parts
                            event_name = f"{away.strip()} vs {home.strip()}"

                    event_button = event.css_first(".event-button a")
                    if not event_button: continue
                    href = event_button.attributes.get("href")

                    start_str = event.css_first(".event-countdown").attributes.get("data-start")
                    event_dt = datetime.fromisoformat(start_str.replace(" ", "T")).replace(tzinfo=timezone.utc)

                    key = f"[{sport}] {event_name} ({TAG})"
                    events[key] = {
                        "sport": sport,
                        "event": event_name,
                        "link": href,
                        "event_ts": event_dt.timestamp(),
                    }
        except Exception as e:
            log.error(f"Error fetching {sport_id}: {e}")
            
    return events

async def scrape():
    now = datetime.now(timezone.utc)
    date_today = now.strftime("%Y-%m-%d")
    date_tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    tasks = [
        refresh_html_cache(d, s_id) 
        for d in [date_today, date_tomorrow] 
        for s_id in CATEGORIES.values()
    ]
    
    results = await asyncio.gather(*tasks)
    all_events = {k: v for data in results for k, v in data.items()}
    
    start_threshold = (now - timedelta(hours=1)).timestamp()
    end_threshold = (now + timedelta(minutes=1)).timestamp()
    
    live_events = [
        v for v in all_events.values() 
        if start_threshold <= v["event_ts"] <= end_threshold
    ]
    
    m3u_output = ["#EXTM3U"]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        for ev in live_events:
            page = await context.new_page()
            try:
                # Playwright navigates to find the actual streaming URL
                await page.goto(ev["link"], wait_until="networkidle", timeout=15000)
                final_url = page.url
                
                title = f"[{ev['sport']}] {ev['event']} ({TAG})"
                
                # Format requested: #EXTINF:-1 group-title="Streamhub", {title}
                m3u_output.append(f'#EXTINF:-1 group-title="Streamhub", {title}')
                m3u_output.append(final_url)
                
                log.info(f"Added: {title}")
            except Exception as e:
                log.warning(f"Failed to process {ev['link']}: {e}")
            finally:
                await page.close()
                
        await browser.close()

    # --- SAVE TO STREAMHUB.M3U8 ---
    with open("streamhub.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_output))
        
    log.info(f"Done! Playlist saved to streamhub.m3u8 with {len(live_events)} streams.")

if __name__ == "__main__":
    asyncio.run(scrape())
