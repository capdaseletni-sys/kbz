import nodriver as uc
import asyncio
from bs4 import BeautifulSoup
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

async def get_online_models(limit=20):
    print("🌐 Launching stealth browser with container-specific flags...")
    
    # Passing sandbox=False directly in start is the key for GitHub Runners
    browser = await uc.start(
        headless=True,
        sandbox=False, 
        browser_args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run"
        ]
    )
    
    try:
        page = await browser.get("https://chaturbate.com/")
        print("⏳ Waiting for model list (bypassing Cloudflare)...")
        
        # Increased timeout for slower cloud CPUs
        await page.wait_for("ul.list", timeout=60)
        
        content = await page.get_content()
        soup = BeautifulSoup(content, "html.parser")
        
        usernames = []
        for a in soup.select('ul.list li div.title a'):
            name = a.get('href').strip('/')
            if name and len(usernames) < limit:
                usernames.append(name)
        
        return usernames
    finally:
        if browser:
            await browser.stop()

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
                print(f"🔗 Extracting Link: {name}")
                info = ydl.extract_info(f"https://chaturbate.com/{name}/", download=False)
                url = info.get('url')
                if url:
                    playlist += f"#EXTINF:-1, {name}\n{url}\n"
            except:
                continue

    with open("chat.m3u8", "w") as f:
        f.write(playlist)
    print(f"✅ chat.m3u8 saved!")

if __name__ == "__main__":
    # Use the nodriver-provided loop helper to avoid 'Event loop is closed' errors
    try:
        uc.loop().run_until_complete(get_online_models(20))
        # Logic to call create_playlist needs the returned names
        # Simplified for final run:
        names = uc.loop().run_until_complete(get_online_models(20))
        if names:
            create_playlist(names)
    except Exception as e:
        print(f"❌ Final Script Attempt Failed: {e}")
