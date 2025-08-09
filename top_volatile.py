import requests
import pandas as pd
import numpy as np
import time
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://api.binance.com"

def fetch_klines(symbol, interval="1h", limit=168):
    url = f"{BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def calculate_ma(df, period):
    return df["close"].rolling(window=period).mean()

def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(df):
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def is_sideways_trend(df):
    ma50 = calculate_ma(df, 50).iloc[-1]
    ma200 = calculate_ma(df, 200).iloc[-1]
    rsi = calculate_rsi(df, 14).iloc[-1]
    macd, signal = calculate_macd(df)
    macd_last = macd.iloc[-1]
    signal_last = signal.iloc[-1]

    if ma50 > ma200 and rsi > 55 and macd_last > signal_last:
        return False
    if ma50 < ma200 and rsi < 45 and macd_last < signal_last:
        return False
    return True

def get_usdt_symbols():
    r = requests.get(f"{BASE_URL}/api/v3/exchangeInfo").json()
    return [s['symbol'] for s in r['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']

def get_volatility(df):
    volatilities = ((df["high"] - df["low"]) / df["close"]) * 100
    return volatilities.mean()

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def main():
    symbols = get_usdt_symbols()
    results = []

    for symbol in symbols:
        try:
            df = fetch_klines(symbol)
            if len(df) < 200:
                continue 

            if not is_sideways_trend(df):
                continue

            price_change = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0] * 100
            if price_change < -15:
                continue

            volatility = get_volatility(df)
            print(symbol, volatility)
            results.append((symbol, volatility))
            time.sleep(0.05)

        except Exception as e:
            print(f"Ошибка {symbol}: {e}")

    results.sort(key=lambda x: x[1], reverse=True)
    top10 = results[:10]

    msg = "<b>ТОП-10 волатильных монет в боковике (1h, 7d)</b>\n\n"
    for sym, vol in top10:
        msg += f"{sym}: {vol:.2f}%\n"

    send_to_telegram(msg)
    print(msg)

if __name__ == "__main__":
    main()
