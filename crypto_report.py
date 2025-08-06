import requests
import pandas as pd
import os
from dotenv import load_dotenv
import openai
from openai import OpenAI

load_dotenv()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = "https://api.binance.com"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

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

def calculate_atr(df, period=14):
    df["prev_close"] = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["prev_close"])
    tr3 = abs(df["low"] - df["prev_close"])
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(period).mean()
    return df

def calculate_macd(df):
    short_ema = df["close"].ewm(span=12, adjust=False).mean()
    long_ema = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = short_ema - long_ema
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    return df

def calculate_ma_slopes_and_crosses(df):
    df["MA50_slope"] = df["MA50"].diff()
    df["MA200_slope"] = df["MA200"].diff()

    df["GoldenCross"] = (df["MA50"].shift(1) < df["MA200"].shift(1)) & (df["MA50"] > df["MA200"])
    df["DeathCross"] = (df["MA50"].shift(1) > df["MA200"].shift(1)) & (df["MA50"] < df["MA200"])

    return df

def determine_market_state(df):
    last = df.iloc[-1]

    rsi = last["RSI48"]
    ma50 = last["MA50"]
    ma200 = last["MA200"]
    atr = last["ATR"]
    macd = last["MACD"]
    signal = last["Signal"]
    ma50_slope = last["MA50_slope"]
    golden_cross = last["GoldenCross"]
    death_cross = last["DeathCross"]

    if pd.isna(rsi) or pd.isna(ma50) or pd.isna(ma200):
        return "🟨 Н/Д (недостаточно данных)"

    diff_pct = abs(ma50 - ma200) / ma200 * 100
    info = []

    if golden_cross:
        info.append("✨ Golden Cross")
    elif death_cross:
        info.append("💀 Death Cross")

    if ma50 > ma200 and macd > signal and rsi > 55 and ma50_slope > 0:
        trend = "🟩 *Восходящий тренд*"
    elif ma50 < ma200 and macd < signal and rsi < 45 and ma50_slope < 0:
        trend = "🟥 *Нисходящий тренд*"
    elif 45 <= rsi <= 55 and diff_pct <= 1:
        trend = "🟦 *Боковик*"
    else:
        trend = "🟨 *Нейтральный*"

    info.append(trend)
    return " | ".join(info)

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

def get_chatgpt_forecast(summary_text):
    prompt = (
        "Ты — криптовалютный аналитик. На основе технических индикаторов (RSI, MA50, MA200, MACD и состояние рынка), "
        "проанализируй следующие криптовалюты и сделай краткий 📊 *прогноз на 24 часа* на русском языке. "
        "Пиши живо, с использованием эмодзи (📈, 📉, ⚠️, 🔁, ✅ и т.д.), но не переусердствуй. "
        "Не дублируй цифры — они уже есть выше. Пиши кратко и по делу.\n\n"
        "Также для каждой монеты обязательно укажи, стоит ли *остановить* или *запустить* grid-бота 🔁. "
        "Учитывай, что grid-боты эффективны в боковике и узком диапазоне 📉📈. "
        "В случае тренда (вверх или вниз) их лучше останавливать.\n\n"
        f"{summary_text}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=700
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ChatGPT error: {e}")
        return "⚠️ Ошибка при генерации прогноза от ChatGPT."

def main():
    messages = []

    for symbol in SYMBOLS:
        try:
            df = fetch_klines(symbol, INTERVAL)
            df = calculate_indicators(df)
            df = calculate_atr(df)
            df = calculate_macd(df)
            df = calculate_ma_slopes_and_crosses(df)

            last = df.iloc[-1]

            rsi = last["RSI48"]
            ma50 = last["MA50"]
            ma200 = last["MA200"]
            macd = last["MACD"]
            signal = last["Signal"]
            atr = last["ATR"]
            trend = determine_market_state(df)

            messages.append(
                f"*{symbol}*\n"
                f"🧮 RSI(48): `{rsi:.8f}`\n"
                f"📏 MA50: `{ma50:.8f}`\n"
                f"📐 MA200: `{ma200:.8f}`\n"
                f"📊 MACD: `{macd:.8f}` / Signal: `{signal:.8f}`\n"
                f"📉 ATR(14): `{atr:.8f}`\n"
                f"{trend}\n"
            )

        except Exception as e:
            messages.append(f"*{symbol}* — error: {e}")

    summary_for_gpt = "\n".join(messages)
    chatgpt_forecast = get_chatgpt_forecast(summary_for_gpt)

    final_msg = "*Crypto 4h Report 📊*\n\n" + summary_for_gpt
    final_msg += "\n\n*Прогноз 💬 (на 24 часа):*\n" + chatgpt_forecast

    send_telegram(final_msg)

if __name__ == "__main__":
    main()
