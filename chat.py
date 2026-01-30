import undetected_chromedriver as uc
import time

def scrape_with_stealth(username):
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # Headless often triggers 403; keep it False first
    
    driver = uc.Chrome(options=options)
    driver.get(f"https://chaturbate.com/get_edge_hls_url_ajax/?room_slug={username}")
    
    # Wait for Cloudflare to finish its 'Checking your browser' dance
    time.sleep(5) 
    
    # Extract the JSON response from the page body
    raw_text = driver.find_element('tag name', 'body').text
    print(f"Server Response: {raw_text}")
    
    driver.quit()

scrape_with_stealth("username_here")
