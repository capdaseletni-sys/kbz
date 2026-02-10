import os
import requests
import json
import random
import time
from datetime import datetime

# --- CONFIGURATION ---
API_EVENTS = os.getenv("PIXELSPORTS_API_URL", "https://pixelsport.tv/backend/livetv/events/")
BASE = "https://pixelsport.tv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_proxy_list():
    """Fetches a fresh list of proxies from multiple sources."""
    log("[*] Scavenging for US HTTPS proxies...")
    proxy_urls = [
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=us&ssl=yes",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt"
    ]
    all_proxies = []
    for url in proxy_urls:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                all_proxies.extend(r.text.splitlines())
        except:
            continue
    return list(set(all_proxies)) # Remove duplicates

def fetch_events():
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": BASE + "/",
        "Origin": BASE
    }

    proxies = get_proxy_list()
    random.shuffle(proxies)
    
    # Try up to 10 different proxies
    for i in range(min(10, len(proxies))):
        proxy_addr = proxies[i]
        proxy_dict = {"http": f"http://{proxy_addr}", "https": f"http://{proxy_addr}"}
        
        log(f"[*] Attempt {i+1}: Trying proxy {proxy_addr}...")
        try:
            response = requests.get(API_EVENTS, headers=headers, proxies=proxy_dict, timeout=8)
            
            if response.status_code == 200:
                events = response.json().get("events", [])
                log(f"✅ Success! Found {len(events)} events using proxy.")
                return events
            else:
                log(f"⚠️ Proxy returned status {response.status_code}. Moving to next...")
        except Exception as e:
            log(f"❌ Proxy failed (Connection Error).")
    
    # Final backup: Try direct (even if we think it's blocked)
    log("[!] All proxies failed. Attempting final direct connection...")
    try:
        r = requests.get(API_EVENTS, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("events", [])
    except:
        pass

    log("💀 Completely blocked. No data retrieved.")
    return []

def build_playlist(events):
    playlist = ["#EXTM3U"]
    for ev in events:
        name = ev.get("match_name", "Live Event")
        category = ev.get("channel", {}).get("TVCategory", {}).get("name", "Sports")
        logo = ev.get("competitors1_logo", "")
        channels = ev.get("channel", {})

        for idx in [1, 2]:
            url = channels.get(f"server{idx}URL")
            if url and str(url).startswith("http"):
                playlist.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{name} [S{idx}]')
                # Important: IPTV players also need the UA/Referer to play the stream
                playlist.append(f"{url}|User-Agent={UA}&Referer={BASE}/")
    return "\n".join(playlist)

def main():
    events = fetch_events()
    if events:
        m3u = build_playlist(events)
        with open("pixelsport.m3u", "w", encoding="utf-8") as f:
            f.write(m3u)
        log("🚀 Playlist updated!")
    else:
        log("❌ Script finished with no data.")

if __name__ == "__main__":
    main()
