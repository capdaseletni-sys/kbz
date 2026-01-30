import yt_dlp

def save_to_playlist(username):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
    url = f"https://chaturbate.com/{username}/"
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get('url')
            
            if stream_url:
                with open("chat.m3u8", "w") as f:
                    # M3U8 standard formatting
                    f.write(f"#EXTM3U\n#EXTINF:-1, {username}\n{stream_url}")
                print(f"✅ chat.m3u8 created successfully for {username}")
            else:
                print("❌ Stream URL not found.")
        except Exception as e:
            print(f"⚠️ yt-dlp error: {e}")

save_to_playlist("username_here")
