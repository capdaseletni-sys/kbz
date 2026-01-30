import yt_dlp
import requests
from bs4 import BeautifulSoup
import time

def get_online_usernames(pages=2):
    print(f"🕵️ Searching for online models across {pages} pages...")
    usernames = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for i in range(1, pages + 1):
        try:
            url = f"https://chaturbate.com/?page={i}"
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            # Find the title links which contain model names
            links = soup.select('ul.list li div.title a')
            for a in links:
                name = a.get('href').replace('/', '')
                if name: usernames.append(name)
        except Exception as e:
            print(f"⚠️ Page {i} error: {e}")
    return list(set(usernames))

def fetch_streams(usernames):
    playlist_content = "#EXTM3U\n"
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'extract_flat': True,
        'source_address': '0.0.0.0', 'impersonate': 'chrome',
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name in usernames:
            try:
                print(f"🔗 Getting link for: {name}")
                info = ydl.extract_info(f"https://chaturbate.com/{name}/", download=False)
                stream_url = info.get('url')
                if stream_url:
                    playlist_content += f"#EXTINF:-1, {name}\n{stream_url}\n"
            except:
                continue # Skip models that trigger 403 or are offline
            time.sleep(1) # Be gentle to avoid IP bans

    with open("all_online.m3u8", "w") as f:
        f.write(playlist_content)
    print("✅ Created all_online.m3u8 with available streams.")

if __name__ == "__main__":
    online_names = get_online_usernames(2) # Scrape ~120 models
    fetch_streams(online_names)
