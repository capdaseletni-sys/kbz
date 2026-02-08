import requests

def fetch_pixel_events():
    url = "https://pixelsport.tv/backend/livetv/events"
    
    # Adding a User-Agent header is good practice to prevent the request from 
    # being blocked by basic bot security.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check for HTTP errors (404, 500, etc.)
        
        # Parse the JSON data
        events = response.json()
        
        print(f"{'MATCH NAME':<40} | {'SERVER 1 URL'}")
        print("-" * 80)

        for event in events:
            # Using .get() prevents the script from crashing if a key is missing
            name = event.get('match_name', 'N/A')
            url_server = event.get('server1URL', 'N/A')
            
            print(f"{name:<40} | {url_server}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    fetch_pixel_events()
