import json
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launching with specific arguments to look more like a real user
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # STEP 1: Visit the homepage first to "clear" the Cloudflare wall
            print("Visiting homepage to clear security challenges...")
            await page.goto("https://pixelsport.tv/", wait_until="networkidle")
            
            # Wait a few seconds for any automated challenges to resolve
            await page.wait_for_timeout(7000)

            # STEP 2: Now navigate to the API endpoint
            print("Navigating to API endpoint...")
            await page.goto("https://pixelsport.tv/backend/livetv/events", wait_until="networkidle")
            
            # Get the text content of the page
            content = await page.locator("body").inner_text()
            
            # Clean the content (sometimes browser adds extra tags)
            content = content.strip()

            if content.startswith("[") or content.startswith("{"):
                data = json.loads(content)
                print(f"\n{'MATCH NAME':<45} | {'SERVER 1 URL'}")
                print("-" * 90)
                
                for event in data:
                    name = event.get('match_name', 'N/A')
                    url_s1 = event.get('server1URL', 'N/A')
                    print(f"{name:<45} | {url_s1}")
            else:
                print("Failed: Content is not JSON. Cloudflare might still be active.")
                print("Page start:", content[:200])
                await page.screenshot(path="cloudflare_block.png")

        except Exception as e:
            print(f"Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
