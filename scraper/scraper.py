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
import requests
from utils import message_hash
import logging
logger = logging.getLogger(__name__)

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

            logger.info('Successfully launched a real browser !')     
        except Exception as e:
            logger.error(f"An error occurred: {e}")


    
    async def run(self):

        # Ensure browser context exists
        if not self.context:
            await self.launch_browser()

        # Close existing leboncoin tabs
        await self.close_tabs(pattern='leboncoin')

        # Open a new tab and go to leboncoin
        page = await self.context.new_page()
        await page.goto("https://www.leboncoin.fr/")
        await page.wait_for_load_state("networkidle")

        # Authenticate session
        await self.connect(page)
        logger.info("Session successfully authenticated.")

        await page.wait_for_load_state("networkidle")

        # Get saved searches
        self.search_items = await page.locator(
            'section[aria-labelledby="recent-searches-title"] a'
        ).element_handles()

        if not self.search_items:
            logger.warning("No saved searches found.")
            return {"status": "no_saved_searches"}

        # Wait randomly between 3–10 seconds
        await asyncio.sleep(random.uniform(3, 10))

        logger.info("Using saved search item to retrieve listings...")
        await self.get_listings(self.search_items[0])

        logger.info("Checking for new messages...")
        await self.handle_messages()

        
    
    async def has_new_messages(self, conversation):

        """
        returns TRue if the conversations has new messsages else False 
        """

        return True
    
    async def handle_messages(self):
        """
        checks the messages page for new messages and replying automatically 

        """
        if not self.context:
            await self.launch_browser()

        page = await self.context.new_page()
        await page.goto("https://www.leboncoin.fr/")
        await page.wait_for_load_state("networkidle")

        await self.connect(page)
        await page.wait_for_load_state("networkidle")

        messages_button = page.locator('a[aria-label="Messages"]').first
        await asyncio.sleep(random.uniform(1, 4.3))
        await messages_button.click()
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(random.uniform(1, 4.3))

        conversations = await page.locator('div[aria-label="Liste des conversations"] ul li a').all()

        to_be_processed = [conversation  for conversation in conversations if await self.has_new_messages(conversation)]

        for conv in to_be_processed:
            await asyncio.sleep(random.uniform(1, 4.3))
            await conv.click()
            await page.wait_for_load_state("networkidle")
            conv_id = page.url.split('/')[-1]
            listing_id = self.database_manager.get_listing_id(conv_id)
            #using the saved messages get the last one and compute its hash 
            last_hash=''
            with open(os.path.join('./sessions', f"{listing_id}.json")) as f :
                messages= json.loads(f)
                last_hash= message_hash(messages[-1])


            



           # get new message 
            
            seller_message= ""
            messages_list = page.locator('div[aria-label="Conversation] ol li ').all()
            for msg in messages_list[-1::]:
                msg_text = await msg.inner_text()
                msg_hash = message_hash(msg_text)
                if msg_hash != last_hash:
                    seller_message += '/n' + msg_text
                else :
                    break

            
            


            
            # send it to server get reply 

            data = {
            "chat_id": listing_id,
            "role": "user",
            "content":seller_message
            }

            print(data)
            
            response = requests.post(url ='http://localhost:8080/chat', json= data)
            if response.status_code==200:
                to_send= json.loads(response.content)['reply']
            # send the message 

            text_area = page.locator('textarea[aria-label="Ecrire mon message"]').first
            await asyncio.sleep(random.uniform(1, 4.3))
            await text_area.click()

         


            await asyncio.sleep(random.uniform(1, 4.3))
            await text_area.fill(to_send)

            send_button= page.get_by_role("button", name="Envoyer mon message")
            await asyncio.sleep(random.uniform(1, 4.3))
            await send_button.click()
            await page.wait_for_load_state("networkidle")       

            # it is time Now to evaluate the conversation for termination 

            data = {
            "chat_id": listing_id,
            }
            ready =False 
            response = requests.post(url ='http://localhost:8080/evaluate', json= data)
            if response.status_code==200:
                ready= json.loads(response.content)['status']
            if ready :
                # send email with full report 



            








    async def close_tabs(self, pattern=' '):
        """
        Close all open pages whose URL contains pattern .
        Useful for cleanup after scraping.
        """
        try:
            for page in self.context.pages:
                if pattern in page.url.lower():
                    print(f"Closing tab: {page.url}")
                    await page.close()
        except Exception as e:
            print(f"Error while closing tabs: {e}")

    async def get_listings(self, search_item):
        try:
            async with self.context.expect_page() as search_page:
                await search_item.click(modifiers=["Control"])
                search_page = await search_page.value
                await search_page.wait_for_load_state("domcontentloaded")

                listings = await search_page.locator(
                    'ul[data-test-id="listing-column"] > li:not([id]) > article a'
                ).element_handles()

                print(f"Found {len(listings)} listings.")

                for listing in listings:
                    time.sleep(random.uniform(1, 5))
                    link = await listing.get_attribute("href")
                    if not link:
                        continue

                    listing_id = link.split("/")[-1]
                    if self.database_manager.exists(listing_id):
                        print("listing already in DB, stopping here...")
                        break

                    async with self.context.expect_page() as listing_page:
                        await listing.click(modifiers=["Control"])
                        listing_page = await listing_page.value
                        self.pages[listing_id] = listing_page
                        await listing_page.wait_for_load_state("load")
                        await self.get_listing_details(listing_id, listing_page)

        except Exception as e:
            print(f"Error in get_offers: {e}")

    async def get_listing_details(self, listing_id, page):
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

            listing = {
                "id": listing_id,
                "title": title,
                "price": price,
                "url": url,
                "location": location,
                "date": date_text,
                "criteria": criteria,
                "description": description,
            }

           
            print(f"Saving listing: {listing_id}")
            self.database_manager.save_listing(listing)

            context = f"""

                "title": {title},
                "price": {price},
                "location": {location},
                "date": {date_text},
                "criteria": {criteria},
    
            """

            user_message_content = f"""
            {description}

            {context}
            """


            # sending first contact mesaage 

            data = {
            "chat_id": listing_id,
            "role": "user",
            "content":user_message_content
            }

            print(data)
            to_send = ""
            response = requests.post(url ='http://localhost:8080/chat', json= data)
            if response.status_code==200:
                to_send= json.loads(response.content)['reply']
            # send the message 

            contact_button = page.get_by_role("button", name="Contacter")
            await asyncio.sleep(random.uniform(1, 4.3))
            await contact_button.click()


            # text area 

            text_area = page.locator('textarea[id="body"]').first
            await asyncio.sleep(random.uniform(1, 4.3))
            await text_area.click()

            delete_button = page.get_by_role("button", name="Supprimer le message") 
            await asyncio.sleep(random.uniform(1, 4.3))
            await delete_button.click()


            await asyncio.sleep(random.uniform(1, 4.3))
            await text_area.fill(to_send)

            send_button= page.get_by_role("button", name="Envoyer")
            await asyncio.sleep(random.uniform(1, 4.3))
            await send_button.click()
            await page.wait_for_load_state("networkidle")


            see_conversation =  page.get_by_role("button", name="Voir ma conversation")
            await asyncio.sleep(random.uniform(1, 4.3))
            await see_conversation.click()
            await page.wait_for_load_state("networkidle")

            # save mapping between listing id and conversation id 
            url = page.url
            conversation_id = url.split('/')[-1]
            conv = {
                'conv_id': conversation_id,
                'listing_id': listing_id
            }
            
            self.database_manager.save_conversation(conv)






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


@app.get("/trigger_scraping")
async def trigger_scraping(background_tasks: BackgroundTasks):
    """
    Trigger the scraping process asynchronously.
    Example:
    requests.get("http://127.0.0.1:8080/trigger_scraping")
    """
    scraper = LeBonCoinScraper()
    background_tasks.add_task(scraper.run)
    return {"status": "Scraping started in background"}

@app.get("/handle_messages")
async def handle_messages(background_tasks: BackgroundTasks):
    """
    handle messages  asynchronously.
    """
    scraper = LeBonCoinScraper()
    background_tasks.add_task(scraper.handle_messages)
    return {"status": "Hnadling messages started in background"}



# ========== Run app directly ==========
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8079)
