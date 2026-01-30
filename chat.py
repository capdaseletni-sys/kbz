import yt_dlp
import sys
from yt_dlp.networking.impersonate import ImpersonateTarget

def get_chaturbate_m3u8(username, proxy=None):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'source_address': '0.0.0.0', # Force IPv4
        'impersonate': ImpersonateTarget.from_str('chrome'),
        # Adding a proxy is the only way to escape GitHub's banned IP range
        'proxy': proxy if proxy else None, 
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
    }
    
    url = f"https://chaturbate.com/{username}/"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"🔍 Bypassing Cloudflare for {username} via Proxy: {bool(proxy)}...")
            info = ydl.extract_info(url, download=False)
            m3u8_url = info.get('url')
            
            if m3u8_url:
                with open("chat.m3u8", "w") as f:
                    f.write(f"#EXTM3U\n#EXTINF:-1, {username}\n{m3u8_url}")
                print(f"✅ Success! Saved to chat.m3u8")
            else:
                print("❌ Link not found. Is the model offline?")
    except Exception as e:
        print(f"⚠️ Bypass Failed: {e}")

if __name__ == "__main__":
    target_user = sys.argv[1] if len(sys.argv) > 1 else "target_username"
    # To use a proxy: get_chaturbate_m3u8(target_user, "http://user:pass@host:port")
    get_chaturbate_m3u8(target_user)
