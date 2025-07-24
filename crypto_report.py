import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://api.binance.com"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BONKUSDT", "SHIBUSDT", "DOGEUSDT", "TRUMPUSDT", "PEPEUSDT"]
INTERVAL = "4h"
RSI_PERIOD = 48

def fetch_klines(symbol, interval, limit=250):
    url = f"{BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])

def calculate_indicators(df):
    df["close"] = df["close"].astype(float)

    if len(df) < 200:
        ma50_period = min(50, len(df))
        ma200_period = min(200, len(df))
    else:
        ma50_period = 50
        ma200_period = 200

    df["MA50"] = df["close"].rolling(window=ma50_period).mean()
    df["MA200"] = df["close"].rolling(window=ma200_period).mean()

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(RSI_PERIOD).mean()
    avg_loss = loss.rolling(RSI_PERIOD).mean()
    rs = avg_gain / avg_loss
    df["RSI48"] = 100 - (100 / (1 + rs))

    return df

def determine_market_state(df):
    last = df.iloc[-1]

    rsi = last["RSI48"]
    ma50 = last["MA50"]
    ma200 = last["MA200"]

    if ma50 is None or ma200 is None or pd.isna(ma50) or pd.isna(ma200):
        return "🟨 Н/Д (недостаточно данных)"

    diff_pct = abs(ma50 - ma200) / ma200 * 100

    if 45 <= rsi <= 55 and diff_pct <= 1:
        return "🟦 *Боковик*"
    elif ma50 > ma200 * 1.01 and rsi > 55:
        return "🟩 *Восходящий тренд*"
    elif ma50 < ma200 * 0.99 and rsi < 45:
        return "🟥 *Нисходящий тренд*"
    else:
        return "🟨 *Нейтральный*"

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
        print(f"Telegram error: {e}")

def main():
    messages = []

    for symbol in SYMBOLS:
        try:
            df = fetch_klines(symbol, INTERVAL)
            df = calculate_indicators(df)
            last = df.iloc[-1]

            rsi = last["RSI48"]
            ma50 = last["MA50"]
            ma200 = last["MA200"]
            trend = determine_market_state(df)

            

            messages.append(
                f"*{symbol}*\n"
                f"🧮 RSI(48): `{rsi:.8f}`\n"
                f"📏 MA50: `{ma50:.8f}`\n"
                f"📐 MA200: `{ma200:.8f}`\n"
                f"{trend}\n"
            )
        except Exception as e:
            messages.append(f"*{symbol}* — error: {e}")

    final_msg = "*Crypto 4h Report 📊*\n\n" + "\n".join(messages)
    send_telegram(final_msg)

if __name__ == "__main__":
    main()
