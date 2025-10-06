import sqlite3
import logging
# Add this line 👇
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect("leboncoin_offers.db")
        self.cursor = self.conn.cursor()
        self.initialize()

    def initialize(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                url TEXT,
                location TEXT,
                date TEXT,
                description TEXT
            )
            """)
        self.conn.commit()
        
    def save_offer(self, offer):
        self.cursor.execute("""
        INSERT OR REPLACE INTO offers (id, title, price, url, location, date, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            offer["id"],
            offer["title"],
            offer["price"],
            offer["url"],
            offer["location"],
            offer["date"],
            offer['description']
        ))
        self.conn.commit()


if __name__ == '__main__':
    offer = {
    "id": "123456789",
    "title": "MacBook Pro 2021",
    "price": "1200 €",
    "url": "https://www.leboncoin.fr/offre/informatique/123456789",
    "location": "Paris",
    "date": "2025-10-05",
    "description": "hello"
}
    database_manager = DatabaseManager()
    database_manager.save_offer(offer)
    logger.info("✅ Offer saved locally!")




    
