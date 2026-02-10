import os
import requests
import json
import random
from datetime import datetime

# --- CONFIGURATION ---
API_EVENTS = os.getenv("PIXELSPORTS_API_URL", "https://pixelsport.tv/backend/livetv/events/")
BASE = "https://pixelsport.tv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_free_us_proxy():
    """Scrapes a list of free US proxies to bypass the GitHub block."""
    log("[*] Fetching fresh US proxies...")
    try:
        # Using a reliable free proxy list
        response = requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=us&ssl=all&anonymity=all")
        if response.status_code == 200:
            proxies = response.text.splitlines()
            if proxies:
                # Pick a random one from the top 5 (usually the fastest)
                selected = random.choice(proxies[:5])
                log(f"[*] Selected US Proxy: {selected}")
                return {"http": f"http://{selected}", "https": f"http://{selected}"}
    except Exception as e:
        log(f"⚠️ Proxy fetch failed: {e}")
    return None

def fetch_events():
    log(f"[*] Target: {API_EVENTS}")
    
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": BASE + "/"
    }

    # 1. Try with Proxy first (to bypass GitHub block)
    proxy_list = get_free_us_proxy()
    
    try:
        log("[*] Attempting fetch with US Proxy...")
        response = requests.get(API_EVENTS, headers=headers, proxies=proxy_list, timeout=15)
        
        # 2. If Proxy fails or blocks, try Direct (as a backup)
        if response.status_code != 200:
            log(f"⚠️ Proxy returned {response.status_code}. Trying direct connection...")
            response = requests.get(API_EVENTS, headers=headers, timeout=10)

        response.raise_for_status()
        events = response.json().get("events", [])
        log(f"✅ Success! Found {len(events)} events.")
        return events

    except Exception as e:
        log(f"❌ Both Proxy and Direct failed: {e}")
        return []

def build_playlist(events):
    playlist = ["#EXTM3U"]
    for ev in events:
        name = ev.get("match_name", "Unknown Event")
        category = ev.get("channel", {}).get("TVCategory", {}).get("name", "Sports")
        logo = ev.get("competitors1_logo", "")
        channels = ev.get("channel", {})

        for idx in [1, 2]:
            url = channels.get(f"server{idx}URL")
            if url and str(url).startswith("http"):
                playlist.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{name} [S{idx}]')
                playlist.append(f"{url}|User-Agent={UA}&Referer={BASE}/")
    return "\n".join(playlist)

def main():
    events = fetch_events()
    if not events:
        return

    m3u_content = build_playlist(events)
    with open("pixelsport.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    log("🚀 Playlist updated successfully!")

if __name__ == "__main__":
    main()
