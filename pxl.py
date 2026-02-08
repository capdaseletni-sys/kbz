import json
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def run():
    stealth = Stealth()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Your specific User-Agent
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
        
        context = await browser.new_context(user_agent=ua)
        await stealth.apply_stealth_async(context)
        page = await context.new_page()
        
        url = "https://pixelsport.tv/backend/livetv/events"
        
        try:
            print("Warming up on homepage...")
            await page.goto("https://pixelsport.tv/", wait_until="networkidle")
            await asyncio.sleep(5) 

            print(f"Fetching data for NBA games...")
            await page.goto(url, wait_until="domcontentloaded")

            try:
                raw_json = await page.locator("pre").inner_text(timeout=5000)
            except:
                raw_json = await page.locator("body").inner_text()

            data = json.loads(raw_json)
            events = data.get("events", data) if isinstance(data, dict) else data

            m3u_content = "#EXTM3U\n"
            count = 0
            
            for event in events:
                name = event.get('match_name', '')
                channel = event.get('channel', {})
                category_info = channel.get('TVCategory', {})
                sport_name = category_info.get('name', '')

                # --- NBA FILTERING LOGIC ---
                # Checks if "NBA" is in the title or the sport category
                if "NBA" in name.upper() or "NBA" in sport_name.upper():
                    
                    url_s1 = channel.get('server1URL') or event.get('server1URL')
                    
                    if url_s1 and url_s1 != "null":
                        # Domain replacement logic
                        if "hd.bestlive.top:443" in url_s1:
                            url_s1 = url_s1.replace("hd.bestlive.top:443", "hd.pixelhd.online:443")
                        
                        # Formatting the M3U entry
                        m3u_content += f'#EXTINF:-1 group-title="NBA",{name}\n'
                        m3u_content += f'#EXTVLCOPT:http-referrer=https://pixelsport.tv\n'
                        m3u_content += f'#EXTVLCOPT:http-origin=https://pixelsport.tv\n'
                        m3u_content += f'#EXTVLCOPT:http-user-agent={ua}\n'
                        m3u_content += f'{url_s1}\n'
                        count += 1

            with open("pixelsports.m3u8", "w", encoding="utf-8") as f:
                f.write(m3u_content)
            
            if count > 0:
                print(f"Success! {count} NBA games saved to pixelsports.m3u8.")
            else:
                print("No NBA games found at the moment.")

        except Exception as e:
            print(f"Scrape failed: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
