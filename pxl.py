import os
import requests
import json
from datetime import datetime

# --- CONFIGURATION ---
# Use the backend URL you discovered
API_EVENTS = os.getenv("PIXELSPORTS_API_URL", "https://pixelsport.tv/backend/livetv/events/")
BASE = "https://pixelsport.tv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def fetch_events():
    log(f"[*] Fetching events from: {API_EVENTS}")
    
    # Headers exactly matching the working version
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": BASE + "/"
    }

    try:
        # Check current IP and Location for debugging Geo-blocks
        ip_info = requests.get("https://ipapi.co/json/", timeout=5).json()
        log(f"[*] Action Running from: {ip_info.get('ip')} ({ip_info.get('country_name')}, {ip_info.get('city')})")
        
        response = requests.get(API_EVENTS, headers=headers, timeout=20)
        
        if response.status_code == 403:
            log("❌ 403 Forbidden: PixelSport blocked the GitHub Runner IP.")
            log("👉 Hint: This is likely a Geo-block. Try running locally or on a US-based VPS.")
            return []
            
        response.raise_for_status()
        data = response.json()
        
        events = data.get("events", [])
        log(f"✅ Success! Found {len(events)} events.")
        return events

    except Exception as e:
        log(f"❌ Error during fetch: {e}")
        return []

def build_playlist(events):
    playlist = ["#EXTM3U"]
    
    for ev in events:
        name = ev.get("match_name", "Unknown Event")
        category = ev.get("channel", {}).get("TVCategory", {}).get("name", "Sports")
        logo = ev.get("competitors1_logo", "")
        
        # Pull server URLs from the 'channel' object
        channels = ev.get("channel", {})
        
        # Check Server 1 and Server 2
        for idx in [1, 2]:
            url = channels.get(f"server{idx}URL")
            
            # Skip if URL is null, empty, or not a link
            if not url or url == "null" or not str(url).startswith("http"):
                continue
                
            label = f"{name} [S{idx}]"
            playlist.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{label}')
            # Append headers to the URL for player compatibility
            playlist.append(f"{url}|User-Agent={UA}&Referer={BASE}/")

    return "\n".join(playlist)

def main():
    events = fetch_events()
    if not events:
        log("⚠️ No events found. Playlist will not be updated.")
        return

    m3u_content = build_playlist(events)
    
    with open("pixelsport.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    log("🚀 Playlist saved to pixelsport.m3u")

if __name__ == "__main__":
    main()
