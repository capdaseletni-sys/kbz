import undetected_chromedriver as uc
import time

def scrape_with_stealth(username):
    options = uc.ChromeOptions()
    
    # REQUIRED for GitHub Actions / Linux Runners
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        # Initialize the driver with these options
        driver = uc.Chrome(options=options)
        
        # Navigate to the API endpoint
        url = f"https://chaturbate.com/get_edge_hls_url_ajax/?room_slug={username}"
        driver.get(url)
        
        # Cloudflare needs a moment to 'verify' the headless browser
        time.sleep(10) 
        
        # Get the page source or body text
        raw_text = driver.find_element('tag name', 'body').text
        
        if "url" in raw_text:
            print(f"✅ Data Found: {raw_text}")
        else:
            print("❌ Still blocked or model is offline. Body content:", raw_text)
            
        driver.quit()
        
    except Exception as e:
        print(f"⚠️ Execution failed: {e}")

scrape_with_stealth("your_target_username")
