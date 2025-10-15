[1mdiff --git a/scraper/scraper.py b/scraper/scraper.py[m
[1mindex 922491a..8d4beb5 100644[m
[1m--- a/scraper/scraper.py[m
[1m+++ b/scraper/scraper.py[m
[36m@@ -8,6 +8,10 @@[m [mfrom playwright.async_api import async_playwright[m
 from playwright.sync_api import TimeoutError[m
 from database import DatabaseManager[m
 import uvicorn[m
[32m+[m[32mimport requests[m
[32m+[m[32mfrom utils import message_hash[m
[32m+[m[32mimport logging[m
[32m+[m[32mlogger = logging.getLogger(__name__)[m
 [m
 app = FastAPI(title="LeBonCoin Scraper API", version="1.0.0")[m
 [m
[36m@@ -31,36 +35,49 @@[m [mclass LeBonCoinScraper:[m
             self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222/")[m
             self.context = self.browser.contexts[0][m
 [m
[31m-          [m
[32m+[m[32m            logger.info('Successfully launched a real browser !')[m[41m     [m
         except Exception as e:[m
[31m-            print(f"An error occurred: {e}")[m
[31m-            return {"error": str(e)}[m
[32m+[m[32m            logger.error(f"An error occurred: {e}")[m
[32m+[m
 [m
     [m
[31m-    async def scrape(self):[m
[32m+[m[32m    async def run(self):[m
 [m
[32m+[m[32m        # Ensure browser context exists[m
         if not self.context:[m
             await self.launch_browser()[m
 [m
[32m+[m[32m        # Close existing leboncoin tabs[m
         await self.close_tabs(pattern='leboncoin')[m
[32m+[m
[32m+[m[32m        # Open a new tab and go to leboncoin[m
         page = await self.context.new_page()[m
         await page.goto("https://www.leboncoin.fr/")[m
         await page.wait_for_load_state("networkidle")[m
 [m
[32m+[m[32m        # Authenticate session[m
         await self.connect(page)[m
[32m+[m[32m        logger.info("Session successfully authenticated.")[m
[32m+[m
         await page.wait_for_load_state("networkidle")[m
 [m
[31m-        # get saved searches[m
[32m+[m[32m        # Get saved searches[m
         self.search_items = await page.locator([m
             'section[aria-labelledby="recent-searches-title"] a'[m
         ).element_handles()[m
 [m
         if not self.search_items:[m
[31m-            print("No saved searches found.")[m
[32m+[m[32m            logger.warning("No saved searches found.")[m
             return {"status": "no_saved_searches"}[m
 [m
[31m-        time.sleep(random.uniform(3, 10))[m
[31m-        await self.get_offers(self.search_items[0])[m
[32m+[m[32m        # Wait randomly between 3–10 seconds[m
[32m+[m[32m        await asyncio.sleep(random.uniform(3, 10))[m
[32m+[m
[32m+[m[32m        logger.info("Using saved search item to retrieve listings...")[m
[32m+[m[32m        await self.get_listings(self.search_items[0])[m
[32m+[m
[32m+[m[32m        logger.info("Checking for new messages...")[m
[32m+[m[32m        await self.handle_messages()[m
 [m
         [m
     [m
[36m@@ -84,6 +101,9 @@[m [mclass LeBonCoinScraper:[m
         await page.goto("https://www.leboncoin.fr/")[m
         await page.wait_for_load_state("networkidle")[m
 [m
[32m+[m[32m        await self.connect(page)[m
[32m+[m[32m        await page.wait_for_load_state("networkidle")[m
[32m+[m
         messages_button = page.locator('a[aria-label="Messages"]').first[m
         await asyncio.sleep(random.uniform(1, 4.3))[m
         await messages_button.click()[m
[36m@@ -97,10 +117,72 @@[m [mclass LeBonCoinScraper:[m
         for conv in to_be_processed:[m
             await asyncio.sleep(random.uniform(1, 4.3))[m
             await conv.click()[m
[31m-            # get new message [m
[32m+[m[32m            await page.wait_for_load_state("networkidle")[m
[32m+[m[32m            conv_id = page.url.split('/')[-1][m
[32m+[m[32m            listing_id = self.database_manager.get_listing_id(conv_id)[m
[32m+[m[32m            #using the saved messages get the last one and compute its hash[m[41m [m
[32m+[m[32m            last_hash=''[m
[32m+[m[32m            with open(os.path.join('./sessions', f"{listing_id}.json")) as f :[m
[32m+[m[32m                messages= json.loads(f)[m
[32m+[m[32m                last_hash= message_hash(messages[-1])[m
[32m+[m
[32m+[m
[32m+[m[41m            [m
[32m+[m
[32m+[m
[32m+[m
[32m+[m[32m           # get new message[m[41m [m
[32m+[m[41m            [m
[32m+[m[32m            seller_message= ""[m
[32m+[m[32m            messages_list = page.locator('div[aria-label="Conversation] ol li ').all()[m
[32m+[m[32m            for msg in messages_list[-1::]:[m
[32m+[m[32m                msg_text = await msg.inner_text()[m
[32m+[m[32m                msg_hash = message_hash(msg_text)[m
[32m+[m[32m                if msg_hash != last_hash:[m
[32m+[m[32m                    seller_message += '/n' + msg_text[m
[32m+[m[32m                else :[m
[32m+[m[32m                    break[m
[32m+[m
[32m+[m[41m            [m
[32m+[m[41m            [m
[32m+[m
[32m+[m
[32m+[m[41m            [m
             # send it to server get reply [m
[31m-            # type it [m
[31m-            # validate [m
[32m+[m
[32m+[m[32m            data = {[m
[32m+[m[32m            "chat_id": listing_id,[m
[32m+[m[32m            "role": "user",[m
[32m+[m[32m            "content":seller_message[m
[32m+[m[32m            }[m
[32m+[m
[32m+[m[32m            print(data)[m
[32m+[m[41m            [m
[32m+[m[32m            response = requests.post(url ='http://localhost:8080/chat', json= data)[m
[32m+[m[32m            if response.status_code==200:[m
[32m+[m[32m                to_send= json.loads(response.content)['reply'][m
[32m+[m[32m            # send the message[m[41m [m
[32m+[m
[32m+[m[32m            text_area = page.locator('textarea[aria-label="Ecrire mon message"]').first[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await text_area.click()[m
[32m+[m
[32m+[m[41m         [m
[32m+[m
[32m+[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await text_area.fill(to_send)[m
[32m+[m
[32m+[m[32m            send_button= page.get_by_role("button", name="Envoyer mon message")[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await send_button.click()[m
[32m+[m[32m            await page.wait_for_load_state("networkidle")[m[41m       [m
[32m+[m
[32m+[m[32m            # it is time Now to evaluate the conversation for termination[m[41m [m
[32m+[m
[32m+[m
[32m+[m[41m            [m
[32m+[m
 [m
 [m
 [m
[36m@@ -121,41 +203,41 @@[m [mclass LeBonCoinScraper:[m
         except Exception as e:[m
             print(f"Error while closing tabs: {e}")[m
 [m
[31m-    async def get_offers(self, search_item):[m
[32m+[m[32m    async def get_listings(self, search_item):[m
         try:[m
             async with self.context.expect_page() as search_page:[m
                 await search_item.click(modifiers=["Control"])[m
                 search_page = await search_page.value[m
                 await search_page.wait_for_load_state("domcontentloaded")[m
 [m
[31m-                offers = await search_page.locator([m
[32m+[m[32m                listings = await search_page.locator([m
                     'ul[data-test-id="listing-column"] > li:not([id]) > article a'[m
                 ).element_handles()[m
 [m
[31m-                print(f"Found {len(offers)} offers.")[m
[32m+[m[32m                print(f"Found {len(listings)} listings.")[m
 [m
[31m-                for offer in offers:[m
[32m+[m[32m                for listing in listings:[m
                     time.sleep(random.uniform(1, 5))[m
[31m-                    link = await offer.get_attribute("href")[m
[32m+[m[32m                    link = await listing.get_attribute("href")[m
                     if not link:[m
                         continue[m
 [m
[31m-                    offer_id = link.split("/")[-1][m
[31m-                    if self.database_manager.exists(offer_id):[m
[31m-                        print("Offer already in DB, stopping here...")[m
[32m+[m[32m                    listing_id = link.split("/")[-1][m
[32m+[m[32m                    if self.database_manager.exists(listing_id):[m
[32m+[m[32m                        print("listing already in DB, stopping here...")[m
                         break[m
 [m
[31m-                    async with self.context.expect_page() as offer_page:[m
[31m-                        await offer.click(modifiers=["Control"])[m
[31m-                        offer_page = await offer_page.value[m
[31m-                        self.pages[offer_id] = offer_page[m
[31m-                        await offer_page.wait_for_load_state("load")[m
[31m-                        await self.get_offer_details(offer_id, offer_page)[m
[32m+[m[32m                    async with self.context.expect_page() as listing_page:[m
[32m+[m[32m                        await listing.click(modifiers=["Control"])[m
[32m+[m[32m                        listing_page = await listing_page.value[m
[32m+[m[32m                        self.pages[listing_id] = listing_page[m
[32m+[m[32m                        await listing_page.wait_for_load_state("load")[m
[32m+[m[32m                        await self.get_listing_details(listing_id, listing_page)[m
 [m
         except Exception as e:[m
             print(f"Error in get_offers: {e}")[m
 [m
[31m-    async def get_offer_details(self, offer_id, page):[m
[32m+[m[32m    async def get_listing_details(self, listing_id, page):[m
         try:[m
             title = await page.locator('div[data-qa-id="adview_title"]').inner_text()[m
             price = await page.locator('div[data-qa-id="adview_price"]').nth(0).inner_text()[m
[36m@@ -178,8 +260,8 @@[m [mclass LeBonCoinScraper:[m
 [m
             description = await page.text_content('p[id="readme-content"]')[m
 [m
[31m-            offer = {[m
[31m-                "id": offer_id,[m
[32m+[m[32m            listing = {[m
[32m+[m[32m                "id": listing_id,[m
                 "title": title,[m
                 "price": price,[m
                 "url": url,[m
[36m@@ -189,12 +271,93 @@[m [mclass LeBonCoinScraper:[m
                 "description": description,[m
             }[m
 [m
[31m-            print(f"Saving offer: {offer_id}")[m
[31m-            self.database_manager.save_offer(offer)[m
[32m+[m[41m           [m
[32m+[m[32m            print(f"Saving listing: {listing_id}")[m
[32m+[m[32m            self.database_manager.save_listing(listing)[m
[32m+[m
[32m+[m[32m            context = f"""[m
[32m+[m
[32m+[m[32m                "title": {title},[m
[32m+[m[32m                "price": {price},[m
[32m+[m[32m                "location": {location},[m
[32m+[m[32m                "date": {date_text},[m
[32m+[m[32m                "criteria": {criteria},[m
[32m+[m[41m    [m
[32m+[m[32m            """[m
[32m+[m
[32m+[m[32m            user_message_content = f"""[m
[32m+[m[32m            {description}[m
[32m+[m
[32m+[m[32m            {context}[m
[32m+[m[32m            """[m
[32m+[m
[32m+[m
[32m+[m[32m            # sending first contact mesaage[m[41m [m
[32m+[m
[32m+[m[32m            data = {[m
[32m+[m[32m            "chat_id": listing_id,[m
[32m+[m[32m            "role": "user",[m
[32m+[m[32m            "content":user_message_content[m
[32m+[m[32m            }[m
[32m+[m
[32m+[m[32m            print(data)[m
[32m+[m[32m            to_send = ""[m
[32m+[m[32m            response = requests.post(url ='http://localhost:8080/chat', json= data)[m
[32m+[m[32m            if response.status_code==200:[m
[32m+[m[32m                to_send= json.loads(response.content)['reply'][m
[32m+[m[32m            # send the message[m[41m [m
[32m+[m
[32m+[m[32m            contact_button = page.get_by_role("button", name="Contacter")[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await contact_button.click()[m
[32m+[m
[32m+[m
[32m+[m[32m            # text area[m[41m [m
[32m+[m
[32m+[m[32m            text_area = page.locator('textarea[id="body"]').first[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await text_area.click()[m
[32m+[m
[32m+[m[32m            delete_button = page.get_by_role("button", name="Supprimer le message")[m[41m [m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await delete_button.click()[m
[32m+[m
[32m+[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await text_area.fill(to_send)[m
[32m+[m
[32m+[m[32m            send_button= page.get_by_role("button", name="Envoyer")[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await send_button.click()[m
[32m+[m[32m            await page.wait_for_load_state("networkidle")[m
[32m+[m
[32m+[m
[32m+[m[32m            see_conversation =  page.get_by_role("button", name="Voir ma conversation")[m
[32m+[m[32m            await asyncio.sleep(random.uniform(1, 4.3))[m
[32m+[m[32m            await see_conversation.click()[m
[32m+[m[32m            await page.wait_for_load_state("networkidle")[m
[32m+[m
[32m+[m[32m            # save mapping between listing id and conversation id[m[41m [m
[32m+[m[32m            url = page.url[m
[32m+[m[32m            conversation_id = url.split('/')[-1][m
[32m+[m[32m            conv = {[m
[32m+[m[32m                'conv_id': conversation_id,[m
[32m+[m[32m                'listing_id': listing_id[m
[32m+[m[32m            }[m
[32m+[m[41m            [m
[32m+[m[32m            self.database_manager.save_conversation(conv)[m
[32m+[m
[32m+[m
[32m+[m
[32m+[m
[32m+[m
 [m
         except Exception as e:[m
             print(f"Error getting offer details: {e}")[m
 [m
[32m+[m
[32m+[m
[32m+[m
     async def connect(self, page):[m
         try:[m
             mon_compte = page.locator("a[aria-label='Mon compte']").first[m
[36m@@ -232,10 +395,10 @@[m [masync def trigger_scraping(background_tasks: BackgroundTasks):[m
     """[m
     Trigger the scraping process asynchronously.[m
     Example:[m
[31m-    requests.get("http://127.0.0.1:8080/get-offers")[m
[32m+[m[32m    requests.get("http://127.0.0.1:8080/trigger_scraping")[m
     """[m
     scraper = LeBonCoinScraper()[m
[31m-    background_tasks.add_task(scraper.scrape)[m
[32m+[m[32m    background_tasks.add_task(scraper.run)[m
     return {"status": "Scraping started in background"}[m
 [m
 @app.get("/handle_messages")[m
