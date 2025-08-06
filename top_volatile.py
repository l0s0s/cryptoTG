import requests
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

EXCLUDED_WORDS = ['UP', 'DOWN', 'BULL', 'BEAR', 'ETF', '1000', 'TUSD', 'FDUSD', 'USDⓈ']
LIMIT = 15
MAX_TREND_PERCENT = 3.0  

def is_clean_symbol(symbol):
    return symbol.endswith('USDT') and all(word not in symbol for word in EXCLUDED_WORDS)

def get_top_sideways(limit=10):
    try:
        res = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(e)
        return []

    sideways = []
    for item in data:
        symbol = item['symbol']
        if not is_clean_symbol(symbol):
            continue

        try:
            price_change = float(item['priceChangePercent'])
            high = float(item['highPrice'])
            low = float(item['lowPrice'])
            avg = float(item['weightedAvgPrice'])

            if abs(price_change) <= MAX_TREND_PERCENT and avg > 0:
                amplitude = (high - low) / avg * 100
                sideways.append({
                    "symbol": symbol,
                    "amplitude": amplitude,
                    "change": price_change
                })
        except:
            continue

    sorted_sideways = sorted(sideways, key=lambda x: x['amplitude'], reverse=True)
    return sorted_sideways[:limit]

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

def format_sideways_message(pairs):
    lines = ["🌀 *Top Sideways (Flat) Volatility Coins*"]
    for p in pairs:
        lines.append(f"`{p['symbol']}`: амплитуда {p['amplitude']:.2f}%, изменение {p['change']:+.2f}%")
    return "\n".join(lines)

if __name__ == "__main__":
    top_flat = get_top_sideways(LIMIT)
    if top_flat:
        message = format_sideways_message(top_flat)
        send_telegram_message(message)
