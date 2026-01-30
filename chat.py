import yt_dlp
import requests
from bs4 import BeautifulSoup
import sys
from yt_dlp.networking.impersonate import ImpersonateTarget

def get_online_usernames(limit=10):
    print(f"🕵️ Scanning Chaturbate for the first {limit} online models...")
    usernames = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        # We scrape the main page to get names
        res = requests.get("https://chaturbate.com/", headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Look for the model names in the title links
        for a in soup.select('ul.list li div.title a'):
            name = a.get('href').strip('/')
            if name and len(usernames) < limit:
                usernames.append(name)
    except Exception as e:
        print(f"⚠️ Failed to scrape model list: {e}")
    
    return usernames

def create_mega_playlist(usernames):
    playlist_content = "#EXTM3U\n"
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'source_address': '0.0.0.0', 
        'impersonate': ImpersonateTarget.from_str('chrome'),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name in usernames:
            try:
                print(f"🔗 Extracting: {name}")
                info = ydl.extract_info(f"https://chaturbate.com/{name}/", download=False)
                stream_url = info.get('url')
                if stream_url:
                    playlist_content += f"#EXTINF:-1, {name}\n{stream_url}\n"
            except Exception:
                print(f"⏩ Skipping {name} (Private or blocked)")
                continue

    with open("chat.m3u8", "w") as f:
        f.write(playlist_content)
    print(f"✅ Playlist saved with {len(usernames)} streams.")

if __name__ == "__main__":
    # 1. Get list of online names
    names = get_online_usernames(limit=20) # Limit to 20 to avoid GitHub time-outs
    # 2. Convert names to m3u8 links
    if names:
        create_mega_playlist(names)
    else:
        print("❌ No models found.")
