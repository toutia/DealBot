import asyncio
import random
from playwright.async_api import async_playwright
import time
from database import DatabaseManager


class LeBonCoinScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.contexts = {}  
        self.search_items=[]
        self.pages= {}
        self.database_manager= DatabaseManager()

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
            time.sleep(random.uniform(3,10))
            
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
        async with self.context.expect_page() as search_page:
                # make it more human by simulating mouse mouvement + clicking outside the center 
                await search_item.click(modifiers=["Control"])
                search_page = await search_page.value
                await search_page.wait_for_load_state("domcontentloaded")
                offers =  await search_page.locator('ul[data-test-id="listing-column"] > li:not([id]) > article a ').element_handles()
          
                print(len(offers))
                for offer in offers[:3]:
                    time.sleep(random.uniform(1,10))
                    link = await offer.get_attribute("href")
                    offer_id = link.split('/')[-1]
     
                    async with self.context.expect_page() as offer_page:
                        await offer.click(modifiers=["Control"])
                        offer_page = await  offer_page.value
                        self.pages[offer_id]= offer_page
                        await offer_page.wait_for_load_state("domcontentloaded")
                        await self.get_offer_details(offer_id , offer_page)

                print(self.pages)

        time.sleep(10)

    async def get_offer_details(self,offer_id , page):
        title = await page.locator('div[data-qa-id="adview_title"]').inner_text() 
        price  = await page.locator('div[data-qa-id="adview_price"] ').nth(0).inner_text()
        url =  page.url
        try:
            location =  await page.locator('section[id="map"] p').inner_text()
        except :
            location = 'not found'
        date_text = await page.locator('h2:text("À propos de l’annonce")').locator('..').locator('span').nth(1).inner_text()
        criteria = await page.locator('div[data-qa-id="criteria_container"] ').inner_text()
        description =  await page.locator('p[id="readme-content"] ').inner_text()

        offer = {
            "id": offer_id,
            "title": title,
            "price": price,
            "url": url,
            "location": location,
            "date": date_text,
            "criteria": criteria,
            "description": description
        }

        self.database_manager.save_offer(offer)
                






        

if __name__ == "__main__":
    scraper = LeBonCoinScraper()
    asyncio.run(scraper.launch_browser())
