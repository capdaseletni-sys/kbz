import json
import cloudscraper
import time

# Configuration
BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"
OUTPUT_FILE = "pixelsports.m3u8"

LIVE_TV_LOGO = "https://pixelsport.tv/static/media/PixelSportLogo.1182b5f687c239810f6d.png"
LIVE_TV_ID = "24.7.Dummy.us"

# Headers for playback compatibility
VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VLC_REFERER = f"{BASE}/"

LEAGUE_INFO = {
    "NFL": ("NFL.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Maxx.png", "NFL"),
    "MLB": ("MLB.Baseball.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Baseball3.png", "MLB"),
    "NHL": ("NHL.Hockey.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Hockey2.png", "NHL"),
    "NBA": ("NBA.Basketball.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Basketball-2.png", "NBA"),
    "NASCAR": ("Racing.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Motorsports2.png", "NASCAR"),
    "UFC": ("UFC.Fight.Pass.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/CombatSports2.png", "UFC"),
    "SOCCER": ("Soccer.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Soccer.png", "Soccer"),
    "BOXING": ("PPV.EVENTS.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Combat-Sports.png", "Boxing"),
}

def fetch_json(url):
    """Uses cloudscraper to bypass 403 Forbidden errors"""
    try:
        # Create scraper instance
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        response = scraper.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[!] Error {response.status_code} for {url}")
            return None
    except Exception as e:
        print(f"[!] Connection Error: {e}")
        return None

def collect_links(obj):
    """Cleanly extracts server URLs and avoids duplicates"""
    links = []
    if not obj:
        return links
    for i in range(1, 4):
        key = f"server{i}URL"
        url = obj.get(key)
        if url and str(url).strip().lower() not in ["null", ""]:
            if url not in links:
                links.append(url.strip())
    return links

def get_league_info(name):
    """Maps categories to EPG IDs and Logos"""
    name_lower = name.lower()
    for key, (tvid, logo, group) in LEAGUE_INFO.items():
        if key.lower() in name_lower:
            return tvid, logo, group
    return ("Pixelsports.Dummy.us", LIVE_TV_LOGO, "Sports")

def build_m3u(events, sliders):
    """Generates the M3U string"""
    lines = ["#EXTM3U"]

    # 1. Process Live Match Events
    for ev in events:
        channel_data = ev.get("channel", {})
        links = collect_links(channel_data)
        if not links:
            continue

        title = ev.get("match_name", "Unknown Event").strip()
        logo = ev.get("competitors1_logo") or LIVE_TV_LOGO
        league_name = channel_data.get("TVCategory", {}).get("name", "Sports")
        tvid, _, group_name = get_league_info(league_name)

        for idx, link in enumerate(links, 1):
            # Append suffix if multiple links exist
            suffix = f" [Link {idx}]" if len(links) > 1 else ""
            lines.append(f'#EXTINF:-1 tvg-id="{tvid}" tvg-logo="{logo}" group-title="PixelSport - {group_name}",{title}{suffix}')
            lines.append(f'#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}')
            lines.append(f'#EXTVLCOPT:http-referrer={VLC_REFERER}')
            lines.append(link)

    # 2. Process Slider (24/7) Channels
    for ch in sliders:
        live_data = ch.get("liveTV", {})
        links = collect_links(live_data)
        if not links:
            continue

        title = ch.get("title", "Live Channel").strip()
        for idx, link in enumerate(links, 1):
            suffix = f" [Link {idx}]" if len(links) > 1 else ""
            lines.append(f'#EXTINF:-1 tvg-id="{LIVE_TV_ID}" tvg-logo="{LIVE_TV_LOGO}" group-title="PixelSport - 24/7",{title}{suffix}')
            lines.append(f'#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}')
            lines.append(f'#EXTVLCOPT:http-referrer={VLC_REFERER}')
            lines.append(link)

    return "\n".join(lines)

def main():
    print("[*] Bypassing security and fetching PixelSport data...")
    
    events_raw = fetch_json(API_EVENTS)
    # Pause slightly between requests to be polite
    time.sleep(1) 
    sliders_raw = fetch_json(API_SLIDERS)

    events = events_raw.get("events", []) if isinstance(events_raw, dict) else []
    sliders = sliders_raw.get("data", []) if isinstance(sliders_raw, dict) else []

    if not events and not sliders:
        print("[!] No data retrieved. The site might be down or blocking the scraper.")
        return

    m3u_content = build_m3u(events, sliders)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print("-" * 30)
    print(f"[+] Success! File saved to: {OUTPUT_FILE}")
    print(f"[+] Found {len(events)} Live Events")
    print(f"[+] Found {len(sliders)} 24/7 Channels")
    print("-" * 30)

if __name__ == "__main__":
    main()
