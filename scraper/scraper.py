import asyncio
from playwright.async_api import async_playwright
import time
class LeBonCoinScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.contexts = {}  
        self.search_items=[]

    async def launch_browser(self):
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222/")
            self.context = self.browser.contexts[0]
            page = await self.context.new_page()
            await page.goto("https://www.leboncoin.fr/")

            # the list of saved searches 

            self.search_items = await  page.locator('section[aria-labelledby="recent-searches-title"]  a').element_handles()
            
            # open new page with every search 
            
            await self.get_offers(self.search_items[0])
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()


    
    async def get_offers(self,search_item):
        # open new context 
        # get offers 
        # save them 
        async with self.context.expect_page() as new_page_info:

                await search_item.click(modifiers=["Control"])
                new_page = await new_page_info.value
                await new_page.wait_for_load_state("domcontentloaded")
        time.sleep(10)



        

if __name__ == "__main__":
    scraper = LeBonCoinScraper()
    asyncio.run(scraper.launch_browser())
