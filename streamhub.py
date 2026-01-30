import asyncio
import logging
from datetime import datetime, timedelta, timezone

from playwright.async_api import async_playwright
from selectolax.parser import HTMLParser

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

async def get_sport_events(page, date_str, sport_id):
    """Uses the existing browser page to fetch events and bypass 403s."""
    events = {}
    url = f"{BASE_URL}events/{date_str}?sport_id={sport_id}"
    
    try:
        # Navigate and wait for content to load
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        content = await page.content()
        
        soup = HTMLParser(content)
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
        log.error(f"Error fetching {sport_id} on {date_str}: {e}")
        
    return events

async def scrape():
    now = datetime.now(timezone.utc)
    dates = [now.strftime("%Y-%m-%d"), (now + timedelta(days=1)).strftime("%Y-%m-%d")]
    
    all_events = {}
    m3u_output = ["#EXTM3U"]

    async with async_playwright() as p:
        # Launch browser with a real User-Agent
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 1. Scrape the list of events
        for date_str in dates:
            for sport_name, sport_id in CATEGORIES.items():
                log.info(f"Fetching {sport_name} for {date_str}...")
                category_events = await get_sport_events(page, date_str, sport_id)
                all_events.update(category_events)

        # 2. Filter for Live
        start_ts = (now - timedelta(hours=1)).timestamp()
        end_ts = (now + timedelta(minutes=1)).timestamp()
        
        live_list = [v for v in all_events.values() if start_ts <= v["event_ts"] <= end_ts]
        log.info(f"Found {len(live_list)} live events. Extracting final URLs...")

        # 3. Process each live event to get final URL
        for ev in live_list:
            try:
                await page.goto(ev["link"], wait_until="networkidle", timeout=15000)
                title = f"[{ev['sport']}] {ev['event']} ({TAG})"
                m3u_output.append(f'#EXTINF:-1 group-title="Streamhub", {title}')
                m3u_output.append(page.url)
            except Exception as e:
                log.warning(f"Failed to resolve {ev['link']}: {e}")

        await browser.close()

    # Save output
    with open("streamhub.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_output))
    
    log.info(f"Done! Saved to streamhub.m3u8")

if __name__ == "__main__":
    asyncio.run(scrape())
