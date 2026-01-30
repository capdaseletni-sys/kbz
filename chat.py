import yt_dlp
import sys

def get_chaturbate_m3u8(username):
    # These options are specifically tuned for cloud environments (GitHub Actions)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'source_address': '0.0.0.0',  # Force IPv4 (GitHub IPv6 is often banned)
        'impersonate': 'chrome',      # Use a real browser TLS fingerprint
    }
    
    url = f"https://chaturbate.com/{username}/"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"🔍 Fetching stream for: {username}...")
            info = ydl.extract_info(url, download=False)
            m3u8_url = info.get('url')
            
            if m3u8_url:
                with open("chat.m3u8", "w") as f:
                    f.write(f"#EXTM3U\n#EXTINF:-1, {username}\n{m3u8_url}")
                print(f"✅ Success! Saved to chat.m3u8")
            else:
                print("❌ Stream not found. Is the model offline?")
                
    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    # You can pass the username as an argument or hardcode it
    target = sys.argv[1] if len(sys.argv) > 1 else "your_target_username"
    get_chaturbate_m3u8(target)
