import asyncio
import random
import time
import json
import os
from fastapi import FastAPI, BackgroundTasks
from playwright.async_api import async_playwright
from playwright.sync_api import TimeoutError
from database import DatabaseManager
import uvicorn

app = FastAPI(title="LeBonCoin Scraper API", version="1.0.0")


class LeBonCoinScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.contexts = {}
        self.search_items = []
        self.pages = {}
        self.database_manager = DatabaseManager()
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_path) as f:
            self.credentials = json.load(f)

    async def launch_browser(self):
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222/")
            self.context = self.browser.contexts[0]

            await self.close_leboncoin_tabs()
            page = await self.context.new_page()
            await page.goto("https://www.leboncoin.fr/")
            await page.wait_for_load_state("networkidle")

            await self.connect(page)
            await page.wait_for_load_state("networkidle")

            # get saved searches
            self.search_items = await page.locator(
                'section[aria-labelledby="recent-searches-title"] a'
            ).element_handles()

            if not self.search_items:
                print("No saved searches found.")
                return {"status": "no_saved_searches"}

            time.sleep(random.uniform(3, 10))
            await self.get_offers(self.search_items[0])

        except Exception as e:
            print(f"An error occurred: {e}")
            return {"error": str(e)}

        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

        return {"status": "done"}

    async def close_leboncoin_tabs(self):
        """
        Close all open pages whose URL contains 'leboncoin'.
        Useful for cleanup after scraping.
        """
        try:
            for page in self.context.pages:
                if "leboncoin" in page.url.lower():
                    print(f"Closing tab: {page.url}")
                    await page.close()
        except Exception as e:
            print(f"Error while closing tabs: {e}")

    async def get_offers(self, search_item):
        try:
            async with self.context.expect_page() as search_page:
                await search_item.click(modifiers=["Control"])
                search_page = await search_page.value
                await search_page.wait_for_load_state("domcontentloaded")

                offers = await search_page.locator(
                    'ul[data-test-id="listing-column"] > li:not([id]) > article a'
                ).element_handles()

                print(f"Found {len(offers)} offers.")

                for offer in offers:
                    time.sleep(random.uniform(1, 5))
                    link = await offer.get_attribute("href")
                    if not link:
                        continue

                    offer_id = link.split("/")[-1]
                    if self.database_manager.exists(offer_id):
                        print("Offer already in DB, stopping here...")
                        break

                    async with self.context.expect_page() as offer_page:
                        await offer.click(modifiers=["Control"])
                        offer_page = await offer_page.value
                        self.pages[offer_id] = offer_page
                        await offer_page.wait_for_load_state("load")
                        await self.get_offer_details(offer_id, offer_page)

        except Exception as e:
            print(f"Error in get_offers: {e}")

    async def get_offer_details(self, offer_id, page):
        try:
            title = await page.locator('div[data-qa-id="adview_title"]').inner_text()
            price = await page.locator('div[data-qa-id="adview_price"]').nth(0).inner_text()
            url = page.url

            try:
                location = await page.locator('section[id="map"] p').inner_text()
            except:
                location = "not found"

            date_text = await page.locator('h2:text("À propos de l’annonce")').locator("..").locator("span").nth(1).inner_text()
            criteria = await page.locator('div[data-qa-id="criteria_container"]').inner_text()

            try:
                voir_plus = page.get_by_role("button", name="Voir plus", exact=True)
                await asyncio.sleep(random.uniform(1, 4.3))
                await voir_plus.click()
            except TimeoutError:
                pass

            description = await page.text_content('p[id="readme-content"]')

            offer = {
                "id": offer_id,
                "title": title,
                "price": price,
                "url": url,
                "location": location,
                "date": date_text,
                "criteria": criteria,
                "description": description,
            }

            print(f"Saving offer: {offer_id}")
            self.database_manager.save_offer(offer)

        except Exception as e:
            print(f"Error getting offer details: {e}")

    async def connect(self, page):
        try:
            mon_compte = page.locator("a[aria-label='Mon compte']").first
            await mon_compte.wait_for(state="visible", timeout=random.uniform(20000, 30000))
        except TimeoutError:
            connection_button = page.get_by_role("button", name="Se connecter")
            await asyncio.sleep(random.uniform(1, 4.3))
            await connection_button.click()

            email = page.locator('input[id="email"]')
            await email.fill(self.credentials["email"])
            await asyncio.sleep(random.uniform(1, 2))

            next_btn = page.get_by_role("button", name="Continuer")
            await next_btn.click()

            password = page.locator('input[id="password"]')
            await password.fill(self.credentials["password"])
            await asyncio.sleep(random.uniform(1, 2))

            login_btn = page.get_by_role("button", name="Se connecter")
            await login_btn.click()
            await asyncio.sleep(random.uniform(2, 4))


# ========== FastAPI ROUTES ==========

@app.get("/")
async def home():
    return {"message": "LeBonCoin Scraper API is running!"}


@app.get("/get-offers")
async def trigger_scraping(background_tasks: BackgroundTasks):
    """
    Trigger the scraping process asynchronously.
    Example:
    requests.get("http://127.0.0.1:8080/get-offers")
    """
    scraper = LeBonCoinScraper()
    background_tasks.add_task(scraper.launch_browser)
    return {"status": "Scraping started in background"}


# ========== Run app directly ==========
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8079)
