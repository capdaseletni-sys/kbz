import json
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser (headless for GitHub Actions)
        browser = await p.chromium.launch(headless=True)
        
        # Using a realistic User-Agent is critical
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        url = "https://pixelsport.tv/backend/livetv/events"
        
        print(f"Navigating to {url}...")
        
        try:
            # Navigate and wait for the page to be "idle" (Cloudflare challenge usually clears here)
            response = await page.goto(url, wait_until="networkidle")
            
            # Wait an extra bit just in case of a slow challenge redirect
            await page.wait_for_timeout(5000)

            # Get the content (which should be the JSON string)
            content = await page.inner_text("body")
            data = json.loads(content)

            print(f"{'MATCH NAME':<40} | {'SERVER 1 URL'}")
            print("-" * 80)
            
            for event in data:
                print(f"{event.get('match_name', 'N/A'):<40} | {event.get('server1URL', 'N/A')}")

        except Exception as e:
            print(f"Error during scrape: {e}")
            # If it fails, take a screenshot to see what Cloudflare is showing
            await page.screenshot(path="debug_screenshot.png")
            print("Saved debug_screenshot.png to see the error.")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
