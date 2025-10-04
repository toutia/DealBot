📦 DealBot

DealBot is an AI-powered negotiation assistant for online marketplaces (starting with Leboncoin).
It scouts listings, contacts sellers, engages in multi-turn discussions, negotiates for a better price, and sends you a clean email summary to help close the deal.



✨ Features

🔍 Product Discovery – scrapes marketplace listings (keywords, price, location filters).

💬 Conversational Agent – conducts polite, multi-turn negotiations with sellers.

🎯 Negotiation Strategy – combines simple rules + LLM phrasing for effective offers.

🧠 Memory & Context – tracks conversation history across multiple turns.

📧 Email Notifications – sends you a summary with seller details, final price, and next steps.

⚡ Local or API – run with a local LLaMA model (3B/7B) or connect to OpenAI GPT-4/3.5.



🏗️ Architecture

Scraper → Collects product listings.

Negotiation Agent → LLM-driven conversation engine.

Strategy Module → Sets offers & counteroffers.

Conversation Memory → Stores and summarizes dialogue.

Notifier → Sends report via email or Telegram.

🚀 Quick Start
```
git clone https://github.com/yourusername/dealbot.git
cd dealbot
pip install -r requirements.txt
python dealbot.py
```

📌 Roadmap

 Add multi-marketplace support (Vinted, eBay, etc.)

 Reinforcement learning–based negotiation strategies

 Web dashboard for monitoring deals

 Voice interface (WhatsApp / Telegram bot)


 ⚠️ Disclaimer

DealBot is for research and personal use only. Automated messaging may violate marketplace terms of service — use responsibly.


