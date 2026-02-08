import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from curl_cffi import requests

# --- Configuration ---
TAG = "PIXEL"
SITE_URL = "https://pixelsport.tv/"
BASE_URL = "https://pixelsport.tv/backend/livetv/events"
M3U_FILENAME = "pixelsports.m3u8"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def generate_m3u(events, filename):
    if not events:
        log.warning("No events to write to file.")
        return
    # Added a timestamp comment so the file changes every run, ensuring a Git commit
    m3u_lines = [f"#EXTM3U\n# UPDATED: {datetime.now(timezone.utc).isoformat()}"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" tvg-logo="" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    
    Path(filename).write_text("\n".join(m3u_lines), encoding="utf-8")
    log.info(f"Successfully generated {filename} with {len(events)} events.")

def scrape():
    events = {}
    try:
        log.info(f"Fetching API via Enhanced TLS Impersonation...")
        
        # We simulate a full browser session
        with requests.Session() as s:
            # First, hit the home page to get session cookies
            s.get(SITE_URL, impersonate="chrome124")
            
            # Now hit the API with the full headers a real browser uses
            response = s.get(
                BASE_URL,
                impersonate="chrome124",
                headers={
                    "authority": "pixelsport.tv",
                    "accept": "application/json, text/plain, */*",
                    "accept-language": "en-US,en;q=0.9",
                    "referer": SITE_URL,
                    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                },
                timeout=30
            )

        if response.status_code != 200:
            log.error(f"Failed to fetch. Status: {response.status_code}")
            log.error(f"Response snippet: {response.text[:200]}")
            return

        api_json = response.json()
        now = datetime.now(timezone.utc)

        for event in api_json.get("events", []):
            try:
                clean_date = event["date"].replace(" ", "T")
                event_dt = datetime.fromisoformat(clean_date).replace(tzinfo=timezone.utc)
                
                # Check if event is today
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
                                "id": "Live.Event.us", 
                                "timestamp": now.timestamp()
                            }
            except Exception:
                continue

        generate_m3u(events, M3U_FILENAME)

    except Exception as e:
        log.error(f"Scraper encountered an error: {e}")

if __name__ == "__main__":
    scrape()
