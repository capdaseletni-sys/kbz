import yt_dlp
import sys
from yt_dlp.networking.impersonate import ImpersonateTarget

def get_chaturbate_m3u8(username):
    # We define the impersonate target explicitly to avoid the "not available" error
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'source_address': '0.0.0.0', # Force IPv4
        # We pass a proper ImpersonateTarget object instead of just a string
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
    }
    
    url = f"https://chaturbate.com/{username}/"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"🔍 Attempting bypass for {username}...")
            info = ydl.extract_info(url, download=False)
            m3u8_url = info.get('url')
            
            if m3u8_url:
                with open("chat.m3u8", "w") as f:
                    f.write(f"#EXTM3U\n#EXTINF:-1, {username}\n{m3u8_url}")
                print(f"✅ Success! Created chat.m3u8")
            else:
                print("❌ Stream not found. (Model offline or geo-blocked)")
                
    except Exception as e:
        print(f"⚠️ Bypass Failed: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "your_username"
    get_chaturbate_m3u8(target)
