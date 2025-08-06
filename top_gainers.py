import requests
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXCLUDED_WORDS = ['UP', 'DOWN', 'BULL', 'BEAR', 'ETF', '1000', 'TUSD', 'FDUSD', 'USDⓈ']

def is_clean_symbol(symbol):
    return all(word not in symbol for word in EXCLUDED_WORDS)

def get_top_gainers(limit=10):
    try:
        res = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(e)
        return []

    usdt_pairs = [item for item in data if item['symbol'].endswith('USDT') and is_clean_symbol(item['symbol'])]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)
    return sorted_pairs[:limit]

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(e)

def format_gainers_message(gainers):
    lines = ["📈 *Top Gainers (24h)*"]
    for g in gainers:
        symbol = g['symbol']
        percent = float(g['priceChangePercent'])
        lines.append(f"{symbol}: +{percent:.2f}%")
    return "\n".join(lines)

if __name__ == "__main__":
    gainers = get_top_gainers()
    if gainers:
        message = format_gainers_message(gainers)
        send_telegram_message(message)
