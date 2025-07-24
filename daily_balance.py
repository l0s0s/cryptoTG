import sqlite3
import os
import time
import requests
import hmac
import hashlib
from urllib.parse import urlencode
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DB_FILE = "balance.db"
BASE_URL = "https://api.binance.com"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, data=data)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram send error: {e}")

def get_total_balance():
    client = Client(API_KEY, API_SECRET)
    account = client.get_account()
    prices = {x['symbol']: float(x['price']) for x in client.get_all_tickers()}

    total = 0.0
    for b in account['balances']:
        asset = b['asset']
        free = float(b['free'])
        locked = float(b['locked'])
        amount = free + locked

        if amount == 0:
            continue

        if asset == "USDT":
            total += amount
        else:
            symbol = asset + "USDT"
            price = prices.get(symbol)

            if price:
                total += amount * price

    return round(total, 2)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balance (
            id INTEGER PRIMARY KEY,
            timestamp INTEGER,
            value REAL
        )
    """)
    conn.commit()
    conn.close()

def get_last_balance():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM balance ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_balance(value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO balance (timestamp, value) VALUES (?, ?)", (int(time.time()), value))
    conn.commit()
    conn.close()

def main():
    init_db()
    current = get_total_balance()
    previous = get_last_balance()
    save_balance(current)

    if previous is None:
        msg = f"💰 First recorded balance: *{current} USDT*"
    else:
        diff = current - previous
        emoji = "📈" if diff > 0 else "📉"
        percent = round((diff / previous) * 100, 2) if previous else 0
        msg = f"{emoji} Balance change in 24h:\nNow: *{current} USDT*\nChange: *{diff:+.2f} USDT* ({percent:+.2f}%)"

    send_telegram(msg)

if __name__ == "__main__":
    main()
