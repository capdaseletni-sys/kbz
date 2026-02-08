from curl_cffi import requests
import json

def fetch_pixel_events():
    url = "https://pixelsport.tv/backend/livetv/events"
    
    # We use 'impersonate' to mimic a real Chrome browser handshake
    # This usually bypasses 403 errors where standard 'requests' fails.
    try:
        response = requests.get(
            url, 
            impersonate="chrome120",
            headers={
                "Referer": "https://pixelsport.tv/",
                "Origin": "https://pixelsport.tv",
                "Accept": "application/json, text/plain, */*"
            }
        )

        if response.status_code == 200:
            events = response.json()
            print(f"{'MATCH NAME':<40} | {'SERVER 1 URL'}")
            print("-" * 80)
            
            for event in events:
                name = event.get('match_name', 'No Name')
                url_s1 = event.get('server1URL', 'No URL')
                print(f"{name:<40} | {url_s1}")
        else:
            print(f"Failed with status: {response.status_code}")
            # If it still fails, the site might require a fresh Cookie from your browser
            print("Response text snippet:", response.text[:200])

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    fetch_pixel_events()
