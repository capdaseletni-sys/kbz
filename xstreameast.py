import asyncio
import re
import json
import os
from urllib.parse import urljoin
import httpx
from selectolax.parser import HTMLParser

# Constants
BASE_URL = "https://xstreameast.com"
TAG = "XSTRMEST"
CACHE_FILE = "cache.json"
OUTPUT_FILE = "xstreameast.m3u8"
SPORT_ENDPOINTS = ["mma", "nba", "nfl", "nhl", "soccer", "wwe"]

async def process_event(client: httpx.AsyncClient, url: str, url_num: int):
    # Regex to find the hex-encoded source within the iframe scripts
    valid_m3u8 = re.compile(r'var\s+(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)
    
    try:
        resp = await client.get(url)
        soup = HTMLParser(resp.text)
        iframe = soup.css_first("iframe")
        
        if not iframe or not (iframe_src := iframe.attributes.get("src")) or iframe_src == "about:blank":
            return None

        iframe_resp = await client.get(iframe_src)
        if match := valid_m3u8.search(iframe_resp.text):
            # Decode the hex-encoded string to get the direct .m3u8 URL
            return bytes.fromhex(match[2]).decode("utf-8")
    except Exception:
        pass
    
    return None

async def get_events(client: httpx.AsyncClient):
    events = []
    for sport_path in SPORT_ENDPOINTS:
        try:
            resp = await client.get(urljoin(BASE_URL, f"categories/{sport_path}/"))
            soup = HTMLParser(resp.text)
            
            sport_name = "Live Event"
            if header := soup.css_first("h1.text-3xl"):
                sport_name = header.text(strip=True).split("Streams")[0].strip()

            for card in soup.css("article.game-card"):
                team_elem = card.css_first("h2.text-xl.font-semibold")
                link_elem = card.css_first("a.stream-button")
                live_badge = card.css_first("span.bg-green-600")

                # Only collect events currently marked as LIVE
                if team_elem and link_elem and live_badge and live_badge.text(strip=True) == "LIVE":
                    events.append({
                        "sport": sport_name,
                        "event": team_elem.text(strip=True),
                        "link": link_elem.attributes.get("href"),
                    })
        except Exception:
            continue
    return events

async def scrape():
    # Load cache to avoid redundant processing
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            cache = {}

    # Set a User-Agent to mimic a real browser
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
        print(f"Searching for live events on {BASE_URL}...")
        found_events = await get_events(client)
        
        m3u_lines = ["#EXTM3U"]
        new_cache = {}

        for i, ev in enumerate(found_events, start=1):
            title = f"[{ev['sport']}] {ev['event']} ({TAG})"
            
            # Check cache first
            if title in cache:
                url = cache[title]["url"]
            else:
                url = await process_event(client, ev["link"], i)
            
            if url:
                # Add to M3U list with the specified format
                m3u_lines.append(f'#EXTINF:-1 group-title="xstreameast", {title}')
                m3u_lines.append(url)
                # Update new cache
                new_cache[title] = {"url": url, "link": ev["link"]}

        # Update cache file with only active streams
        with open(CACHE_FILE, "w") as f:
            json.dump(new_cache, f)

        # Write the final playlist
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
        
        print(f"Success! Saved {len(m3u_lines)//2} streams to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(scrape())
