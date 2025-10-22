import os
import asyncio
import threading
import requests
import time
import json
import re
import logging
import aiohttp
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Python Number Checker Bot is Running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', "6224828344:AAF8T-lhNZDl3E8dBRzK7p6NJtIr6Dzj0b8")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 5624278091))

print("🚀 Starting Bot...")
print("📱 Bot Token:", BOT_TOKEN[:10] + "..." if BOT_TOKEN else "Not Found")
print("👑 Admin ID:", ADMIN_ID)

def main():
    # Start Flask server
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Flask server started on port 10000")
    
    # Keep the main thread alive
    while True:
        time.sleep(60)
        print("🤖 Bot is running...")

if __name__ == "__main__":
    main()
