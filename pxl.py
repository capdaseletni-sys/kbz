#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timedelta
from urllib.parse import quote
import requests

# ---------------- CONFIG ---------------- #

BASE = "https://pixelsport.tv"

# ✅ Hardcoded Direct API Link
API_URL = "https://pixelsport.tv/backend/livetv/events"

OUT_VLC = "pixelsports.m3u8"
OUT_TIVI = "pixelsportstivi.m3u8"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"
UA_ENC = quote(UA, safe="")

# ---------------- HELPERS ---------------- #

def log(*a):
    print(*a)
    sys.stdout.flush()

def utc_to_et(utc_str: str) -> str:
    if not utc_str: return ""
    try:
        # Handles 'Z' or '+00:00' offsets
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        # Standard Eastern Time offset (approx -5)
        et = dt - timedelta(hours=5) 
        return et.strftime("%I:%M %p ET %m/%d").replace(" 0", " ")
    except Exception:
        return ""

# ---------------- CORE LOGIC ---------------- #

def fetch_events() -> list:
    log(f"[*] Fetching PixelSports events...")
    try:
        r = requests.get(
            API_URL,
            headers={
                "User-Agent": UA,
                "Accept": "application/json",
                "Referer": f"{BASE}/"
            },
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        
        # Adjusting based on common API structures
        if isinstance(data, dict):
            return data.get("events", [])
        elif isinstance(data, list):
            return data
        return []
        
    except Exception as e:
        log(f"❌ API request failed: {e}")
        return []

def build_playlist(events: list, tivimate: bool = False) -> str:
    out = ["#EXTM3U"]

    for ev in events:
        match_name = ev.get("match_name", "Live Event")
        logo = ev.get("logo", "")
        time_et = utc_to_et(ev.get("date", ""))
        
        display_name = f"{match_name} ({time_et})" if time_et else match_name
        channels = ev.get("channel", {})

        # Mapping API server keys
        mapping = [("server1URL", "Home"), ("server2URL", "Away"), ("server3URL", "Alt")]

        for key, label in mapping:
            url = channels.get(key)
            if not url or str(url).lower() == "null" or not str(url).startswith("http"):
                continue

            extinf = f'#EXTINF:-1 group-title="PixelSport"'
            if logo:
                extinf += f' tvg-logo="{logo}"'
            extinf += f',{display_name} [{label}]'
            
            out.append(extinf)

            if tivimate:
                # TiViMate/OTT Navigator format for headers
                out.append(f"{url}|User-Agent={UA_ENC}&Referer={quote(BASE + '/')}")
            else:
                # Standard VLC/generic player options
                out.append(f"#EXTVLCOPT:http-user-agent={UA}")
                out.append(f"#EXTVLCOPT:http-referrer={BASE}/")
                out.append(url)

    return "\n".join(out)

# ---------------- MAIN ---------------- #

def main():
    events = fetch_events()

    if not events:
        log("❌ No events found or failed to parse API.")
        return

    # Write VLC Playlist
    with open(OUT_VLC, "w", encoding="utf-8") as f:
        f.write(build_playlist(events, tivimate=False))

    # Write TiViMate Playlist
    with open(OUT_TIVI, "w", encoding="utf-8") as f:
        f.write(build_playlist(events, tivimate=True))

    log(f"✔ Successfully generated playlists with {len(events)} events.")
    log(f"✔ Files created: {OUT_VLC}, {OUT_TIVI}")

if __name__ == "__main__":
    main()
