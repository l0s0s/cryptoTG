import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.binance.com/api/v3/ticker/24hr"
TOP_N = 10
QUOTE_ASSET = "USDT" 

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def get_top_volatility():
    response = requests.get(BASE_URL)
    data = response.json()

    usdt_pairs = [
        coin for coin in data 
        if coin['symbol'].endswith(QUOTE_ASSET) and float(coin['lowPrice']) > 0
    ]

    for coin in usdt_pairs:
        high = float(coin['highPrice'])
        low = float(coin['lowPrice'])
        coin['volatility'] = ((high - low) / low) * 100

    sorted_pairs = sorted(usdt_pairs, key=lambda x: x['volatility'], reverse=True)
    top_pairs = sorted_pairs[:TOP_N]

    message = f"📊 *Топ {TOP_N} волатильных монет ({QUOTE_ASSET})* на {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    for coin in top_pairs:
        message += f"• `{coin['symbol']}` — волатильность *{coin['volatility']:.2f}%*, 24ч: {coin['priceChangePercent']}%\n"

    send_to_telegram(message)

if __name__ == "__main__":
    get_top_volatility()
