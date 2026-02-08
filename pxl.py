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
    m3u_lines = ["#EXTM3U"]
    for name, data in events.items():
        sport = name.split(']')[0].replace('[', '') if ']' in name else "Sports"
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{data["id"]}" tvg-logo="" group-title="{sport}",{name}')
        m3u_lines.append(data["url"])
    
    Path(filename).write_text("\n".join(m3u_lines), encoding="utf-8")
    log.info(f"Successfully generated {filename} with {len(events)} events.")

def scrape():
    events = {}
    try:
        log.info(f"Fetching API via TLS Impersonation...")
        
        # This 'impersonate' flag is the secret sauce for Cloudflare
        response = requests.get(
            BASE_URL,
            impersonate="chrome120",
            headers={
                "Referer": SITE_URL,
                "Accept": "application/json",
            },
            timeout=30
        )

        if response.status_code != 200:
            log.error(f"Failed to fetch. Status: {response.status_code}")
            return

        api_json = response.json()
        now = datetime.now(timezone.utc)

        for event in api_json.get("events", []):
            try:
                # Standardize date format
                clean_date = event["date"].replace(" ", "T")
                event_dt = datetime.fromisoformat(clean_date).replace(tzinfo=timezone.utc)
                
                # Only get events for today
                if event_dt.date() != now.date():
                    continue

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
