import nodriver as uc
import asyncio
from bs4 import BeautifulSoup
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

async def get_online_models(limit=20):
    print("🌐 Launching stealth browser to bypass Cloudflare...")
    browser = await uc.start()
    page = await browser.get("https://chaturbate.com/")
    
    # Wait for the model list to actually appear (bypassing the challenge)
    await page.wait_for("ul.list", timeout=30)
    
    # Get the rendered HTML
    content = await page.get_content()
    soup = BeautifulSoup(content, "html.parser")
    
    usernames = []
    for a in soup.select('ul.list li div.title a'):
        name = a.get('href').strip('/')
        if name and len(usernames) < limit:
            usernames.append(name)
            
    await browser.stop()
    return usernames

def create_playlist(usernames):
    playlist = "#EXTM3U\n"
    ydl_opts = {
        'quiet': True, 'extract_flat': True,
        'source_address': '0.0.0.0',
        'impersonate': ImpersonateTarget.from_str('chrome'),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name in usernames:
            try:
                print(f"🔗 Extracting: {name}")
                info = ydl.extract_info(f"https://chaturbate.com/{name}/", download=False)
                url = info.get('url')
                if url:
                    playlist += f"#EXTINF:-1, {name}\n{url}\n"
            except:
                continue

    with open("chat.m3u8", "w") as f:
        f.write(playlist)
    print("✅ Playlist Updated!")

if __name__ == "__main__":
    # nodriver requires an event loop
    loop = asyncio.get_event_loop()
    names = loop.run_until_complete(get_online_models(20))
    if names:
        create_playlist(names)
    else:
        print("❌ Could not bypass verification. Try using a proxy.")
