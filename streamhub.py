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
    events = {}
    url = f"{BASE_URL}events/{date_str}?sport_id={sport_id}"
    
    try:
        # Increased timeout and wait for network to be idle
        await page.goto(url, wait_until="networkidle", timeout=30000)
        content = await page.content()
        soup = HTMLParser(content)
        
        for event in soup.css(".section-event"):
            # Get Team Names
            event_name = "Live Event"
            teams_node = event.css_first(".event-competitors")
            if teams_node:
                raw_text = teams_node.text(strip=True)
                # Handle "vs." or "vs" or " - "
                clean_text = raw_text.replace("vs.", "vs")
                if "vs" in clean_text:
                    parts = clean_text.split("vs")
                    event_name = f"{parts[1].strip()} vs {parts[0].strip()}"
                else:
                    event_name = raw_text

            # Get Link
            btn = event.css_first(".event-button a")
            if not btn: continue
            href = btn.attributes.get("href")
            if not href: continue

            # Get Time
            time_node = event.css_first(".event-countdown")
            if not time_node: continue
            start_str = time_node.attributes.get("data-start")
            if not start_str: continue
            
            event_dt = datetime.fromisoformat(start_str.replace(" ", "T")).replace(tzinfo=timezone.utc)

            # Get Sport Name from parent section if possible, otherwise use a fallback
            key = f"{event_name} ({TAG})"
            events[key] = {
                "event": event_name,
                "link": href,
                "event_ts": event_dt.timestamp(),
            }
    except Exception as e:
        log.error(f"Error on {url}: {e}")
        
    return events

async def scrape():
    now = datetime.now(timezone.utc)
    # Fetch today and tomorrow
    dates = [now.strftime("%Y-%m-%d"), (now + timedelta(days=1)).strftime("%Y-%m-%d")]
    
    all_events = {}
    m3u_output = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a very common User Agent to avoid detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for date_str in dates:
            for sport_name, sport_id in CATEGORIES.items():
                log.info(f"Checking {sport_name} [{date_str}]...")
                category_events = await get_sport_events(page, date_str, sport_id)
                # Inject sport name into results
                for k in category_events:
                    category_events[k]["sport"] = sport_name
                all_events.update(category_events)

        # LOOSER FILTER: Include anything that started in the last 2 hours 
        # OR starts in the next 12 hours.
        start_ts = (now - timedelta(hours=2)).timestamp()
        end_ts = (now + timedelta(hours=12)).timestamp()
        
        live_list = [v for v in all_events.values() if start_ts <= v["event_ts"] <= end_ts]
        
        log.info(f"Found {len(live_list)} upcoming/live events. Processing links...")

        for ev in live_list:
            try:
                # Note: Some sites redirect immediately, page.url captures the final destination
                await page.goto(ev["link"], wait_until="domcontentloaded", timeout=20000)
                final_url = page.url
                
                title = f"[{ev['sport']}] {ev['event']} ({TAG})"
                m3u_output.append(f'#EXTINF:-1 group-title="Streamhub", {title}')
                m3u_output.append(final_url)
                log.info(f"Added: {ev['event']}")
            except Exception as e:
                log.debug(f"Could not resolve {ev['link']}")

        await browser.close()

    with open("streamhub.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_output))
    
    log.info(f"Saved {len(m3u_output)//2} entries to streamhub.m3u8")

if __name__ == "__main__":
    asyncio.run(scrape())
