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
SPORT_ENDPOINTS = ["mma", "nba", "nfl", "nhl", "soccer", "wwe"]

async def process_event(client: httpx.AsyncClient, url: str, url_num: int):
    valid_m3u8 = re.compile(r'var\s+(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)
    
    try:
        resp = await client.get(url)
        soup = HTMLParser(resp.text)
        iframe = soup.css_first("iframe")
        
        if not iframe or not (iframe_src := iframe.attributes.get("src")) or iframe_src == "about:blank":
            return None, None

        iframe_resp = await client.get(iframe_src)
        if match := valid_m3u8.search(iframe_resp.text):
            # Decode the hex-encoded M3U8 URL
            return bytes.fromhex(match[2]).decode("utf-8"), iframe_src
    except Exception as e:
        print(f"Error processing URL {url_num}: {e}")
    
    return None, None

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

                if team_elem and link_elem and live_badge and live_badge.text(strip=True) == "LIVE":
                    events.append({
                        "sport": sport_name,
                        "event": team_elem.text(strip=True),
                        "link": link_elem.attributes.get("href"),
                    })
        except Exception as e:
            print(f"Error fetching {sport_path}: {e}")
    return events

async def scrape():
    # Basic JSON Cache loading
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)

    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"Scraping {BASE_URL}...")
        found_events = await get_events(client)
        
        m3u_lines = ["#EXTM3U"]
        
        for i, ev in enumerate(found_events, start=1):
            title = f"[{ev['sport']}] {ev['event']} ({TAG})"
            
            # Use cache if available, otherwise scrape
            if title in cache:
                url = cache[title]["url"]
            else:
                url, iframe = await process_event(client, ev["link"], i)
                if url:
                    cache[title] = {"url": url, "link": ev["link"]}
            
            if url:
                # Format: #EXTINF:-1 group-title="xstreameast", {title}
                m3u_lines.append(f'#EXTINF:-1 group-title="xstreameast", {title}')
                m3u_lines.append(url)

        # Save Cache
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)

        # Output M3U
        with open("playlist.m3u", "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
        
        print(f"Done! Created playlist.m3u with {len(m3u_lines)//2} streams.")

if __name__ == "__main__":
    asyncio.run(scrape())
