import json
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def run():
    # Initialize the new Stealth object
    stealth = Stealth()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # New recommended way: Apply stealth to the entire context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Apply stealth to all pages in this context
        await stealth.apply_stealth_async(context)
        
        page = await context.new_page()
        url = "https://pixelsport.tv/backend/livetv/events"
        
        try:
            print("Warming up on homepage...")
            await page.goto("https://pixelsport.tv/", wait_until="networkidle")
            await asyncio.sleep(5) 

            print(f"Fetching API: {url}")
            await page.goto(url, wait_until="domcontentloaded")

            # Try to grab the JSON wrapped in <pre> tags
            try:
                raw_json = await page.locator("pre").inner_text(timeout=5000)
            except:
                raw_json = await page.locator("body").inner_text()

            data = json.loads(raw_json)
            events = data.get("events", data) if isinstance(data, dict) else data

            print(f"\n{'MATCH NAME':<45} | {'SERVER 1 URL'}")
            print("-" * 90)

            for event in events:
                name = event.get('match_name', 'N/A')
                channel = event.get('channel', {})
                url_s1 = channel.get('server1URL') or event.get('server1URL', 'N/A')
                print(f"{name[:45]:<45} | {url_s1}")

        except Exception as e:
            print(f"Scrape failed: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
