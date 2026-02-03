import re
import asyncio
import logging
import json
import time
import sys
from urllib.parse import urljoin

try:
    import httpx
    from selectolax.parser import HTMLParser
except ImportError:
    print("Error: Dependencies missing. Run 'pip install httpx selectolax'")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- CONFIGURATION ---
CACHE_PATH = "totalsportk_cache.json"
M3U_FILENAME = "ovogoal.m3u8"
CACHE_EXPIRY = 14400  # 4 hours
BASE_TEMPLATE = "https://ovogoal.plus/totalsportek/nba{}/"
NUM_STREAMS = 10

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

# --- UTILITIES ---
def shorten_nba_teams(text: str) -> str:
    for full_name, short_name in TEAM_MAP.items():
        pattern = re.compile(re.escape(full_name), re.IGNORECASE)
        text = pattern.sub(short_name, text)
    return text

def load_cache():
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_cache(data):
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=4)

# --- CORE LOGIC ---
async def scrape_nba_page(client: httpx.AsyncClient, stream_num: int) -> tuple[str, dict | None]:
    url = BASE_TEMPLATE.format(stream_num)
    valid_m3u8 = re.compile(r'var\s+(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)
    
    # Default title
    display_title = f"NBA Stream {stream_num}"

    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200:
            return display_title, None
        
        soup = HTMLParser(resp.text)
        
        # Try to extract the team names from the page (e.g., <h1> or title)
        header_node = soup.css_first("h1, h2, .entry-title, .match-name")
        if header_node:
            raw_text = header_node.text(strip=True)
            # Remove common fluff and apply abbreviations
            clean_text = raw_text.replace("Live Stream", "").replace("Totalsportek", "").strip()
            display_title = f"[{stream_num}] {shorten_nba_teams(clean_text)}"

        iframe = soup.css_first("iframe")
        if not iframe or not (iframe_src := iframe.attributes.get("src")):
            return display_title, None

        # Fetch iframe with Referer header
        iframe_resp = await client.get(iframe_src, headers={"Referer": url}, timeout=10.0)
        
        if match := valid_m3u8.search(iframe_resp.text):
            raw = match[2]
            try:
                # Handle hex-encoded links
                m3u8_url = bytes.fromhex(raw).decode("utf-8")
            except (ValueError, TypeError):
                # Handle plain text links
                m3u8_url = raw
                
            log.info(f"Success: {display_title}")
            return display_title, {
                "url": m3u8_url,
                "timestamp": time.time(),
                "stream_num": stream_num
            }
    except Exception as e:
        log.debug(f"Error on NBA {stream_num}: {e}")
    
    return display_title, None

async def scrape() -> None:
    cached_data = load_cache()
    current_time = time.time()
    
    # Clean expired cache
    active_cache = {k: v for k, v in cached_data.items() if current_time - v.get("timestamp", 0) < CACHE_EXPIRY}

    # http2=False to avoid the ImportError you encountered
    async with httpx.AsyncClient(
        follow_redirects=True, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        http2=False 
    ) as client:
        
        log.info(f"Processing NBA pages 1 through {NUM_STREAMS}...")
        tasks = [scrape_nba_page(client, i) for i in range(1, NUM_STREAMS + 1)]
        results = await asyncio.gather(*tasks)
        
        for title, data in results:
            if data:
                active_cache[title] = data

    # Generate M3U
    m3u_lines = ["#EXTM3U"]
    # Sort by stream number
    sorted_items = sorted(active_cache.items(), key=lambda x: x[1].get("stream_num", 0))
    
    for title, data in sorted_items:
        if stream_url := data.get("url"):
            m3u_lines.append(f'#EXTINF:-1 group-title="NBA-OVOGOAL", {title}')
            m3u_lines.append(stream_url)

    with open(M3U_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    save_cache(active_cache)
    log.info(f"Done! Created {M3U_FILENAME}")

if __name__ == "__main__":
    asyncio.run(scrape())
