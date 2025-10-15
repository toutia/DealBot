import sqlite3
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect("listings.db")
        self.cursor = self.conn.cursor()
        self.initialize()

    def initialize(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                url TEXT,
                location TEXT,
                date TEXT,
                description TEXT
            )
            
            CREATE TABLE IF NOT EXISTS conversations (
                conv_id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES listings(id)
            );             
            
            """)
        self.conn.commit()
        
    def save_listing(self, listing):
        self.cursor.execute("""
        INSERT OR REPLACE INTO listings (id, title, price, url, location, date, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            listing["id"],
            listing["title"],
            listing["price"],
            listing["url"],
            listing["location"],
            listing["date"],
            listing['description']
        ))
        self.conn.commit()

    def save_conversation(self, conv):
        self.cursor.execute("""
        INSERT OR REPLACE INTO conversations (conv_id, listing_id)
        VALUES (?, ?)
        """, (
            conv["conv_id"],
            conv["listing_id"],
   
        ))
        self.conn.commit()

    def exists(self, listing_id):
        self.cursor.execute("SELECT 1 FROM listings WHERE id = ? LIMIT 1", (listing_id,))
        return self.cursor.fetchone() is not None
    
    def get_listing_id(self, conv_id):
        self.cursor.execute("SELECT listing_id FROM conversations WHERE conv_id = ? LIMIT 1", (conv_id,))
        return self.cursor.fetchone()


if __name__ == '__main__':
    listing = {
    "id": "123456789",
    "title": "MacBook Pro 2021",
    "price": "1200 €",
    "url": "https://www.leboncoin.fr/offre/informatique/123456789",
    "location": "Paris",
    "date": "2025-10-05",
    "description": "hello"
}
    database_manager = DatabaseManager()
    database_manager.save_listing(listing)
    logger.info("✅ listing saved locally!")




    
