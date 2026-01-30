import requests

def save_m3u8_to_file(username, filename="chat.m3u8"):
    url = "https://chaturbate.com/get_edge_hls_url_ajax/"
    
    # These headers mimic a real Chrome browser session
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://chaturbate.com",
        "Referer": f"https://chaturbate.com/{username}/",
    }
    
    data = {"room_slug": username}
    
    try:
        # Using a Session object helps maintain cookies
        session = requests.Session()
        # First, visit the home page to get a CSRF cookie
        session.get("https://chaturbate.com/", headers={"User-Agent": headers["User-Agent"]})
        
        # Now make the POST request
        response = session.post(url, headers=headers, data=data)
        
        if response.status_code == 403:
            print("❌ Still blocked (403). Cloudflare is likely challenging the request.")
            return

        json_data = response.json()
        if json_data.get('success'):
            m3u8_url = json_data.get('url')
            with open(filename, "w") as f:
                f.write(f"#EXTM3U\n{m3u8_url}")
            print(f"✅ Success! Saved to {filename}")
        else:
            print(f"⚠️ Room Error: {json_data.get('room_status')}")

    except Exception as e:
        print(f"⚠️ Error: {e}")

save_m3u8_to_file("username_here")
