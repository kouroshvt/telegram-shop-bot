import os
from flask import Flask
import threading
import asyncio
import bot

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_bot_async():
    """اجرای بات در یک حلقه asyncio جدید"""
    asyncio.run(bot.run_bot())

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot_async)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)