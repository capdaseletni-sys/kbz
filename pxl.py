import json
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def run():
    async with async_playwright() as p:
        # Launch browser with anti-detection args
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        await stealth_async(page)
        
        url = "https://pixelsport.tv/backend/livetv/events"
        
        try:
            print("Warming up on homepage...")
            await page.goto("https://pixelsport.tv/", wait_until="networkidle")
            await asyncio.sleep(5) 

            print(f"Fetching API from {url}...")
            await page.goto(url, wait_until="domcontentloaded")

            # The secret sauce: Look for the <pre> tag where browsers dump raw JSON
            try:
                raw_json = await page.locator("pre").inner_text(timeout=10000)
            except:
                # Fallback to body if <pre> isn't used
                raw_json = await page.locator("body").inner_text()

            data = json.loads(raw_json)
            
            # The structure is usually {"events": [...]} or a direct list []
            events_list = data.get("events", data) if isinstance(data, dict) else data

            print(f"\n{'SPORT':<15} | {'MATCH NAME':<35} | {'SERVER 1 URL'}")
            print("-" * 100)

            for event in events_list:
                # Extracting details based on the structure you shared
                match_name = event.get('match_name', 'N/A')
                
                # Digging into the 'channel' object if it exists
                channel = event.get('channel', {})
                server1 = channel.get('server1URL') or event.get('server1URL', 'N/A')
                
                # Get category/sport if available
                category = channel.get('TVCategory', {})
                sport = category.get('name', 'Live')

                print(f"{sport[:15]:<15} | {match_name[:35]:<35} | {server1}")

        except Exception as e:
            print(f"Scrape failed: {e}")
            await page.screenshot(path="error.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
