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
from utils import message_hash, send_email, get_json_session_path
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
            self.credentials = json.load(f)['leboncoin']


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
        await page.wait_for_load_state("load")

        # Authenticate session
        await self.connect(page)
        logger.info("Session successfully authenticated.")

        await page.wait_for_load_state("load")

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

        response = requests.get(url ='http://localhost:8078/finished_scraping')
        if response.status_code==200:
            logger.info('New scraping session will be scheduled soon !')
        

        
    
    async def get_number_of_new_messages(self, conversation):

        """
        returns TRue if the conversations has new messsages else False 
        """

        badge = conversation.locator('span[data-spark-component="badge"][role="status"]')
        if await badge.is_visible():
                badge_text = await badge.inner_text()
                logger.info(f"🔔 You have {badge_text.strip()} new messages")
                return int(badge_text.strip())

        return 0
    
    async def handle_messages(self):
        """
        checks the messages page for new messages and replying automatically 

        """
        try:
            if not self.context:
                await self.launch_browser()

            page = await self.context.new_page()
            await page.goto("https://www.leboncoin.fr/")
            await page.wait_for_load_state("load")

            await self.connect(page)
            await page.wait_for_load_state("load")
            await asyncio.sleep(random.uniform(1, 4.3))
            messages_button = page.locator('a[aria-label="Messages"]').first
             # check i three is new messages 
            badge = messages_button.locator('span[data-spark-component="badge"][role="status"]')

        except Exception as e:
            logger.error(f"Could not  find the messages button or its status badge :{e}" )

        try:
            if await badge.is_visible():

                try:
                    badge_text = await badge.inner_text()
                    logger.info(f"🔔 You have {badge_text.strip()} new notifications.")
                    
                    await asyncio.sleep(random.uniform(1, 4.3))
                    await messages_button.click()
                    await page.wait_for_load_state("load")
                    await asyncio.sleep(random.uniform(1, 4.3))

                    logger.info(f"checking the conversations in the conversations page .")

                    conversations = await page.locator('div[aria-label="Liste des conversations"] ul li').all()

                
                    logger.info(f'We have {len(conversations)}  conversations to handle')
                except Exception as e :
                    logger.error(f"Could not  access the conversations page :{e}" )

                
                for conv in conversations:
                    new_messages_number = await  self.get_number_of_new_messages(conv)
                    if  new_messages_number== 0:
                        continue
                    await asyncio.sleep(random.uniform(1, 4.3))
                    await conv.click()
                    await page.wait_for_load_state("load")
                    conv_id = page.url.split('/')[-1]
                    logger.info(f'Checking conversation : {conv_id}')
                    listing_id = self.database_manager.get_listing_id(conv_id)
                    if not listing_id:
                        logger.info(f'Ignore this conversation as it not handled by me : {conv_id} : {listing_id}')
                        continue
                   

                # get new message 
                    try: 
                        seller_message= ""
                        messages_list =await page.locator('div[aria-label="Conversation"] ol li ').all()
                        logger.info('Extracting last messages sent by the seller')
                        for msg in messages_list[-new_messages_number:]:
                            msg_text = await msg.inner_text()
                            seller_message += '/n' + msg_text
                    except Exception as e : 
                        logger.error(f'Getting last seller messages within conv {conv_id} Failed: {e}')
                    

                    # send it to server get reply 
                    try:
                        data = {
                        "chat_id": listing_id,
                        "role": "user",
                        "content":seller_message
                        }

                        logger.info('Contacting the LLM to get reply')
                        
                        response = requests.post(url ='http://localhost:8080/chat', json= data)
                        if response.status_code==200:
                            to_send= json.loads(response.content)['reply']
                        # send the message 
                    except Exception as e :
                        logger.error(f'Error while Generating response for last  seller  message  within conv {conv_id} : {e}')
                    

                    try:

                        text_area = page.locator('textarea[aria-label="Ecrire mon message"]').first
                        await asyncio.sleep(random.uniform(1, 4.3))
                        await text_area.click()
                        await asyncio.sleep(random.uniform(1, 4.3))
                        await text_area.fill(to_send)

                        send_button= page.get_by_role("button", name="Envoyer mon message")
                        await asyncio.sleep(random.uniform(1, 4.3))
                        await send_button.click()
                        logger.info(f'Automatically replied to seller : {conv_id}')
                        await page.wait_for_load_state("load")  
                    except Exception as e :
                        logger.error(f'Exception  while Sending  response for last  seller  message  within conv {conv_id}: {e}')


                    # it is time Now to evaluate the conversation for termination 
                    ready = False 
                    try :
                        data = {
                        "chat_id": listing_id,
                        }
                        ready =False 
                        logger.info('Evaluating conversation to check if its ready for report ! ')
                        response = requests.post(url ='http://localhost:8080/evaluate', json= data)
                        if response.status_code==200:
                            ready= json.loads(response.content)['status']
                        
                    except Exception as e :
                        logger.error(f'Error while evaluting  conv {conv_id} for completion: {e}')

                
                    try : 
                        if ready :
                            # send email with full report 
                            # extract the conversation to include it in the eamail
                            
                            send_email(
                                listing_id= listing_id
                            )
                    except Exception as e :
                        logger.error(f'Failed to send report Email: {e}')
            
            else:
                logger.info("✅ No new notifications.")

            
        except Exception as e:
            logger.error(f'Error when handling messages : {e}')


    async def close_tabs(self, pattern=' '):
        """
        Close all open pages whose URL contains pattern .
        Useful for cleanup after scraping.
        """
        try:
            for page in self.context.pages:
                if pattern in page.url.lower():
                    logger.info(f"Closing tab: {page.url}")
                    await page.close()
        except Exception as e:
            logger.info(f"Error while closing tabs: {e}")

    async def get_listings(self, search_item):
        try:
            async with self.context.expect_page() as search_page:
                await search_item.click(modifiers=["Control"])
                search_page = await search_page.value
                await search_page.wait_for_load_state("domcontentloaded")

                listings = await search_page.locator(
                    'ul[data-test-id="listing-column"] > li:not([id]) > article a'
                ).element_handles()

                logger.info(f"Found {len(listings)} listings.")

                for listing in listings[3:]:

                    await asyncio.sleep(random.uniform(1, 5))
                    link = await listing.get_attribute("href")
                    if not link:
                        continue

                    listing_id = link.split("/")[-1]
                    
                    if self.database_manager.exists(listing_id):
                        logger.warning("listing already in DB, stopping here...")
                        break
                    logger.info(f"Getting listing  :  {listing_id}")
                    async with self.context.expect_page() as listing_page:
                        await listing.click(modifiers=["Control"])
                        listing_page = await listing_page.value
                        self.pages[listing_id] = listing_page
                        await listing_page.wait_for_load_state("load")
                        await self.get_listing_details(listing_id, listing_page)

        except Exception as e:
            logger.error(f"Error in get_offers: {e}")



    async def get_listing_details(self, listing_id, page):
        logger.info(f"Getting listing  details :  {listing_id}")
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

           
            logger.info(f"Saving listing: {listing_id}")
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
            logger.info(f"First contact message generation : {listing_id}")

            # sending first contact mesaage 

            data = {
            "chat_id": listing_id,
            "role": "user",
            "content":user_message_content
            }

           

            contact_button = page.get_by_role("button", name="Contacter")
            await asyncio.sleep(random.uniform(1, 4.3))
            await contact_button.click()


            # text area 
            try:

                text_area = page.locator('textarea[id="body"]').first
                await asyncio.sleep(random.uniform(1, 4.3))
                await text_area.click()
            except  Exception as e :
                logger.error(f'Error when contacting the seller : the text area: {e}')
            try:
                to_send = ""
                response = requests.post(url ='http://localhost:8080/chat', json= data)
                if response.status_code==200:
                    to_send= json.loads(response.content)['reply']
                # send the message 
            except  Exception as e :
                logger.error(f'Error when generating the first contact message: {e}')

            try:

                delete_button = page.get_by_role("button", name="Supprimer le message") 
                await asyncio.sleep(random.uniform(1, 4.3))
                await delete_button.click()
           

                await asyncio.sleep(random.uniform(1, 4.3))
                await text_area.fill(to_send)

                send_button= page.get_by_role("button", name="Envoyer")
                await asyncio.sleep(random.uniform(1, 4.3))
                await send_button.click()
                await page.wait_for_load_state("load")

            except  Exception as e :
                logger.error(f'Error while sending the first contact message: {e}')


            try: 
                await asyncio.sleep(random.uniform(6, 8))
                see_conversation =  page.locator("a", has_text="Voir ma conversation").first
                await asyncio.sleep(random.uniform(1, 4.3))
                await see_conversation.click()
                await page.wait_for_load_state("load")
            except  Exception as e :
                logger.error(f'Error while trying to see the first conversation: {e}')    
            

            try:
                # save mapping between listing id and conversation id 
                await asyncio.sleep(random.uniform(3, 8))
                url = page.url
                conversation_id = url.split('/')[-1]
                
            except  Exception as e :
                logger.error(f'Error while getting the conversation id: {e}')    
                
            try :
                conv_data = {
                    'conv_id': conversation_id,
                    'listing_id': listing_id
                }
                self.database_manager.save_conversation(conv_data)
                logger.info(f"First contact message sent and conversation id saved  : {listing_id}: {conversation_id}")
            except  Exception as e :
                logger.error(f'Error while saving the  conversation id in the database: {e}')    

        except Exception as e:
            logger.error(f"Error getting offer details: {e}")




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
