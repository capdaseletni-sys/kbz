from drissionpage import ChromiumPage, ChromiumOptions
import json
import time

def fetch_pixel_events():
    # Set up browser options (run in headless mode so no window pops up)
    co = ChromiumOptions().headless()
    # Adding a real user agent
    co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    page = ChromiumPage(co)
    
    try:
        print("Bypassing Cloudflare... please wait.")
        # Navigate to the API URL directly
        page.get('https://pixelsport.tv/backend/livetv/events')
        
        # Give it a few seconds to solve the challenge and load
        time.sleep(3) 
        
        # Get the raw text from the page (which should be the JSON)
        raw_text = page.json
        
        if not raw_text:
            # If page.json fails, try pulling from the body tag
            raw_text = json.loads(page.ele('tag:body').text)

        print(f"{'MATCH NAME':<40} | {'SERVER 1 URL'}")
        print("-" * 80)

        for event in raw_text:
            name = event.get('match_name', 'N/A')
            url_s1 = event.get('server1URL', 'N/A')
            print(f"{name:<40} | {url_s1}")

    except Exception as e:
        print(f"Failed to bypass: {e}")
    finally:
        page.quit()

if __name__ == "__main__":
    fetch_pixel_events()
