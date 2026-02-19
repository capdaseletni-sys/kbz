import re
import asyncio
import logging
import json
import time
import sys
from functools import partial
from urllib.parse import urljoin, urlparse

try:
    import httpx
    from selectolax.parser import HTMLParser
except ImportError:
    print("Error: Dependencies missing. Run 'pip install httpx selectolax'")
    sys.exit(1)

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

urls: dict[str, dict] = {}
TAG = "TOTALSPRTK"
CACHE_PATH = "totalsportk_cache.json"
M3U_FILENAME = "totalsport.m3u8"

# NBA Team Abbreviations
TEAM_MAP = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS"
}

# Updated Mirror List with live3 as priority
MIRRORS = [
    {"base": "https://live3.totalsportek777.com/", "hex_decode": True},
    {"base": "https://live.totalsportek777.com/", "hex_decode": True},
    {"base": "https://live2.totalsportek777.com/", "hex_decode": False},
]

def fix_txt(s: str) -> str:
    s = " ".join(s.split())
    return s.upper() if s.islower() else s

def shorten_nba_teams(event_name: str) -> str:
    new_name = event_name
    for full_name, short_name in TEAM_MAP.items():
        pattern = re.compile(re.escape(full_name), re.IGNORECASE)
        new_name = pattern.sub(short_name, new_name)
    return new_name

def load_cache():
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cache(data):
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=4)

async def process_event(client, href: str, url_num: int) -> tuple[str | None, str | None]:
    valid_m3u8 = re.compile(r'var\s+(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)
    for mirror in MIRRORS:
        url = urljoin(mirror["base"], href)
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code != 200: continue
            soup = HTMLParser(resp.text)
            iframe = soup.css_first("iframe")
            if not iframe or not (iframe_src := iframe.attributes.get("src")):
                continue
            
            iframe_resp = await client.get(iframe_src, timeout=10.0)
            if match := valid_m3u8.search(iframe_resp.text):
                raw = match[2]
                m3u8_url = bytes.fromhex(raw).decode("utf-8") if mirror["hex_decode"] else raw
                return m3u8_url, iframe_src
        except Exception:
            continue
    return None, None

async def get_events(client, url: str, cached_keys: list[str]) -> list[dict]:
    events = []
    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200: return events
        soup = HTMLParser(resp.text)
        sport = "Live Event"

        for node in soup.css("a"):
            if not node.attributes.get("class"): continue
            if (parent := node.parent) and "my-1" in parent.attributes.get("class", ""):
                if span := node.css_first("span"):
                    sport = span.text(strip=True)

            sport = fix_txt(sport)
            if not (teams := [t.text(strip=True) for t in node.css(".col-7 .col-12")]): continue
            if not (href := node.attributes.get("href")): continue

            href = urlparse(href).path if href.startswith("http") else href
            time_node = node.css_first(".col-3 span")
            
            if time_node and time_node.text(strip=True) == "MatchStarted":
                raw_event_name = " vs ".join(teams)
                event_name = shorten_nba_teams(raw_event_name)
                title = f"[{sport}] {event_name}"
                
                if title not in cached_keys:
                    events.append({"sport": sport, "event": event_name, "href": href, "key": title})
    except Exception as e:
        log.error(f"Failed to fetch events: {e}")
    return events

async def scrape() -> None:
    cached_data = load_cache()
    current_time = time.time()
    # 8-hour cache TTL
    active_cache = {k: v for k, v in cached_data.items() if current_time - v.get("timestamp", 0) < 28800}
    urls.update({k: v for k, v in active_cache.items() if v.get("url")})

    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        base_url = None
        for mirror in MIRRORS:
            try:
                r = await client.get(mirror["base"], timeout=5.0)
                if r.status_code == 200:
                    base_url = str(r.url)
                    log.info(f"Using Mirror: {base_url}")
                    break
            except: continue

        if not base_url: 
            log.error("Could not reach any mirrors.")
            return

        new_events = await get_events(client, base_url, list(active_cache.keys()))

        for i, ev in enumerate(new_events, start=1):
            m3u8, iframe = await process_event(client, ev["href"], i)
            if m3u8:
                entry = {"url": m3u8, "base": iframe, "timestamp": time.time(), "href": ev["href"]}
                active_cache[ev["key"]] = entry
                urls[ev["key"]] = entry
                log.info(f"Success: {ev['key']}")

    m3u_lines = ["#EXTM3U"]
    for title, data in urls.items():
        if stream_url := data.get("url"):
            m3u_lines.append(f'#EXTINF:-1 group-title="Totalsports", {title}')
            m3u_lines.append(stream_url)

    with open(M3U_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    save_cache(active_cache)
    log.info(f"Updated {M3U_FILENAME} with {len(urls)} links.")

if __name__ == "__main__":
    asyncio.run(scrape())
