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
CACHE_EXPIRY = 14400  # 4 hours (streams cycle faster than 8)
BASE_TEMPLATE = "https://ovogoal.plus/totalsportek/nba{}/"
NUM_STREAMS = 10

# --- UTILITIES ---
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
    """Scrapes a specific nba# page for the m3u8 link."""
    url = BASE_TEMPLATE.format(stream_num)
    # This regex looks for the hex-encoded or plain string in the JS variables
    valid_m3u8 = re.compile(r'var\s+(\w+)\s*=\s*"([^"]*)"', re.IGNORECASE)
    title = f"NBA Stream {stream_num}"

    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200: 
            return title, None
        
        soup = HTMLParser(resp.text)
        
        # Try to find a better title from the page content if available
        # Adjust selector if the page has an <h1> or <h3> with the team names
        team_header = soup.css_first("h1, h2, .entry-title")
        if team_header:
            title = f"[{stream_num}] {team_header.text(strip=True)}"

        iframe = soup.css_first("iframe")
        if not iframe or not (iframe_src := iframe.attributes.get("src")):
            return title, None

        # Fetch the iframe content to find the actual m3u8
        # We use the current page as the Referer
        iframe_resp = await client.get(iframe_src, headers={"Referer": url}, timeout=10.0)
        
        if match := valid_m3u8.search(iframe_resp.text):
            raw = match[2]
            # Try to hex decode, if it fails, use raw (handles both Mirror types)
            try:
                m3u8_url = bytes.fromhex(raw).decode("utf-8")
            except ValueError:
                m3u8_url = raw
                
            log.info(f"Found: {title}")
            return title, {
                "url": m3u8_url,
                "timestamp": time.time(),
                "stream_num": stream_num
            }
    except Exception as e:
        log.debug(f"Error scraping NBA {stream_num}: {e}")
    
    return title, None

async def scrape() -> None:
    cached_data = load_cache()
    current_time = time.time()
    
    # Clean old cache
    active_cache = {k: v for k, v in cached_data.items() if current_time - v.get("timestamp", 0) < CACHE_EXPIRY}

    async with httpx.AsyncClient(
        follow_redirects=True, 
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        http2=True
    ) as client:
        
        log.info(f"Checking {NUM_STREAMS} NBA stream pages...")
        tasks = [scrape_nba_page(client, i) for i in range(1, NUM_STREAMS + 1)]
        results = await asyncio.gather(*tasks)
        
        # Update cache with new results
        for title, data in results:
            if data:
                active_cache[title] = data

    # 4. Generate M3U
    m3u_lines = ["#EXTM3U"]
    # Sort by stream number for a clean list
    sorted_items = sorted(active_cache.items(), key=lambda x: x[1].get("stream_num", 0))
    
    for title, data in sorted_items:
        if stream_url := data.get("url"):
            m3u_lines.append(f'#EXTINF:-1 group-title="NBA-OVOGOAL", {title}')
            m3u_lines.append(stream_url)

    with open(M3U_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    save_cache(active_cache)
    log.info(f"M3U updated. {len(m3u_lines)//2} active streams saved.")

if __name__ == "__main__":
    asyncio.run(scrape())
