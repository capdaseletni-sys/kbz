import nodriver as uc
import asyncio
from bs4 import BeautifulSoup
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

async def get_online_models(limit=20):
    print("🌐 Launching stealth browser with sandbox disabled...")
    
    # CRITICAL: These arguments allow nodriver to run in GitHub Actions
    browser = await uc.start(
        headless=True,
        browser_args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
    )
    
    try:
        page = await browser.get("https://chaturbate.com/")
        # Give Cloudflare time to "Verify you are human"
        print("⏳ Waiting for Cloudflare verification...")
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
        await browser.stop()

def create_playlist(usernames):
    playlist = "#EXTM3U\n"
    # yt-dlp 2026 logic with impersonation
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
    print(f"✅ chat.m3u8 updated with {len(usernames)} streams!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    names = loop.run_until_complete(get_online_models(20))
    if names:
        create_playlist(names)
    else:
        print("❌ Could not find models. Check if the site layout changed.")
