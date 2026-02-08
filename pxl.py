import requests

def fetch_pixel_events():
    url = "https://pixelsport.tv/backend/livetv/events"
    
    # More comprehensive headers to bypass the 403 block
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://pixelsport.tv/",
        "Origin": "https://pixelsport.tv",
        "Connection": "keep-alive"
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 403:
            print("Still getting 403. The server might be using Cloudflare or a WAF.")
            return

        response.raise_for_status()
        events = response.json()
        
        for event in events:
            print(f"Match: {event.get('match_name')} | URL: {event.get('server1URL')}")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_pixel_events()
