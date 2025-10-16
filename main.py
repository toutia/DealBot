import logging
import random
import asyncio
from fastapi import FastAPI, BackgroundTasks
import os, requests, uvicorn

SESSIONS_DIR = os.path.join(os.path.dirname('__file__'), 'sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI()
# first scraping session 
logger.info("Application started")
requests.get("http://127.0.0.1:8079/trigger_scraping")
logger.info(f'The scraper is launched.')
# Possible intervals in seconds
INTERVALS = [600, 300, 420, 840]


async def trigger_next_scrape():
    """
    Wait a random interval and then trigger the next scrape.
    """

    interval = random.choice(INTERVALS)
    logger.info(f"Next scrape will be triggered in {interval} seconds")
    await asyncio.sleep(interval)
    requests.get("http://127.0.0.1:8079/trigger_scraping")


@app.get("/finished_scraping")
async def finished_scraping(background_tasks: BackgroundTasks):
    """
    Call this endpoint when scraping finishes. 
    It schedules the next scrape after a random interval.
    """
    logger.info("Received finished_scraping signal")
    background_tasks.add_task(trigger_next_scrape)
    return {"status": "next scrape scheduled"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8078)