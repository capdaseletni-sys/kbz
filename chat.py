import nodriver as uc
import asyncio
from bs4 import BeautifulSoup
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

async def get_online_models(limit=20):
    print("🌐 Launching stealth browser with mandatory sandbox bypass...")
    
    # In 2026, 'sandbox=False' is a direct keyword in nodriver.start
    # This is more effective than just passing it in browser_args
    browser = await uc.start(
        headless=True,
        sandbox=False, # THIS IS THE CRITICAL FIX
        browser_args=[
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run"
        ]
    )
    
    try:
        page = await browser.get("https://chaturbate.com/")
        print("⏳ Waiting for site to stabilize...")
        
        # We wait for the main grid to load
        await page.wait_for("ul.list", timeout=45)
        
        content = await page.get_content()
        soup = BeautifulSoup(content, "html.parser")
        
        usernames = []
        for a in soup.select('ul.list li div.title a'):
            name = a.get('href').strip('/')
            if name and len(usernames) < limit:
                usernames.append(name)
        
        return usernames
    finally:
        # Prevent the 'NoneType' error by checking if browser exists before stopping
        if browser:
            await browser.stop()

def create_playlist(usernames):
    playlist = "#EXTM3U\n"
    ydl_opts = {
        'quiet': True, 
        'extract_flat': True,
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
    print(f"✅ chat.m3u8 saved with {len(usernames)} entries.")

if __name__ == "__main__":
    # Fix for DeprecationWarning and Python 3.12 logic
    try:
        names = asyncio.run(get_online_models(20))
        if names:
            create_playlist(names)
        else:
            print("❌ No models found.")
    except Exception as e:
        print(f"❌ Script failed: {e}")
