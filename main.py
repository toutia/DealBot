import logging
import requests
import asyncio
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Application started")


    while True:
        interval = random.choice([600, 300, 420, 840])
            
        requests.get("http://127.0.0.1:8079/trigger_scraping")
        logger.info(f'The agent is launched. It will be triggered again in  {interval}  seconds')
        asyncio.sleep(interval)


if __name__ == "__main__":
    main()