from playwright.sync_api import sync_playwright

def scrape_chaturbate():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://chaturbate.com/")
        
        # Wait for the model cards to load
        page.wait_for_selector('.room_list')
        
        # Extract names and viewer counts
        models = page.query_selector_all('.room_list li')
        for model in models:
            name = model.query_selector('.title a').inner_text()
            viewers = model.query_selector('.viewers').inner_text()
            print(f"Model: {name.strip()} | Viewers: {viewers}")
            
        browser.close()
