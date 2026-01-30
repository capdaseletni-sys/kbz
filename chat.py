import requests

def save_m3u8_to_file(username, filename="chat.m3u8"):
    # Chaturbate internal API endpoint
    url = "https://chaturbate.com/get_edge_hls_url_ajax/"
    
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    data = {"room_slug": username}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        json_data = response.json()
        
        if json_data.get('success'):
            m3u8_url = json_data.get('url')
            
            # Creating the content for a standard M3U playlist file
            m3u_content = f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1280000\n{m3u8_url}"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(m3u_content)
                
            print(f"✅ Success! Playlist saved to {filename}")
            print(f"🔗 Stream URL: {m3u8_url}")
        else:
            print(f"❌ Error: {json_data.get('room_status', 'Unknown error')}")
            
    except Exception as e:
        print(f"⚠️ Failed to connect: {e}")

# Replace 'username' with the actual model name
save_m3u8_to_file("username_here")
