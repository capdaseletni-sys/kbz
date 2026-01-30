import nodriver as uc
import asyncio
from bs4 import BeautifulSoup
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

async def get_online_models(limit=20):
    print("🌐 Initializing browser (Bypassing Sandbox for GitHub Actions)...")
    
    # We use sandbox=False + specific flags for container environments
    browser = await uc.start(
        headless=True,
        sandbox=False,  # This tells nodriver to bypass the root check
        browser_args=[
            "--no-sandbox",                  # Double-down on sandbox bypass
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",       # Prevents crash in small Docker shm
            "--disable-gpu",
            "--no-first-run",
            "--remote-debugging-port=9222"   # Explicit port helps connectivity
        ]
    )
    
    try:
        # Give the browser a moment to breathe before requesting
        await asyncio.sleep(2)
        
        page = await browser.get("https://chaturbate.com/")
        print("⏳ Browser started. Waiting for verification...")
        
        # Solving the Cloudflare challenge can take 10-30 seconds on GitHub
        await page.wait_for("ul.list", timeout=60)
        
        content = await page.get_content()
        soup = BeautifulSoup(content, "html.parser")
        
        usernames = []
        for a in soup.select('ul.list li div.title a'):
            name = a.get('href').strip('/')
            if name and len(usernames) < limit:
                usernames.append(name)
        
        return usernames
    except Exception as e:
        print(f"⚠️ Scraping failed: {e}")
        return []
    finally:
        # Fix the AttributeError: 'NoneType' by checking connection status
        if browser and hasattr(browser, 'connection') and browser.connection:
            await browser.stop()
        else:
            print("🚫 Browser connection was never established. Skipping cleanup.")

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
                print(f"🔗 Extracting: {name}")
                info = ydl.extract_info(f"https://chaturbate.com/{name}/", download=False)
                url = info.get('url')
                if url:
                    playlist += f"#EXTINF:-1, {name}\n{url}\n"
            except:
                continue

    with open("chat.m3u8", "w") as f:
        f.write(playlist)
    print("✅ Playlist generated.")

if __name__ == "__main__":
    # Use asyncio.run for cleaner loop management in Python 3.12
    try:
        online_names = asyncio.run(get_online_models(20))
        if online_names:
            create_playlist(online_names)
        else:
            print("❌ No models found or verification failed.")
    except Exception as total_error:
        print(f"🚨 Fatal Error: {total_error}")
