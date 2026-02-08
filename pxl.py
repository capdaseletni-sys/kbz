import cloudscraper
import json

def fetch_data():
    # Create a scraper instance that bypasses Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    url = "https://pixelsport.tv/backend/livetv/events"
    
    try:
        response = scraper.get(url)
        
        if response.status_code == 200:
            events = response.json()
            print(f"{'MATCH NAME':<40} | {'SERVER 1 URL'}")
            print("-" * 80)
            for event in events:
                print(f"{event.get('match_name', 'N/A'):<40} | {event.get('server1URL', 'N/A')}")
        else:
            print(f"Failed. Status: {response.status_code}")
            # If we still get a 403, Cloudflare is in 'High' security mode
            if "Cloudflare" in response.text:
                print("Cloudflare detected and blocked the request.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_data()
