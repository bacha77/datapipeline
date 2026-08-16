import sqlite3
import requests
import os
import pandas as pd
import yfinance as yf
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Configuration & Secrets
DB_NAME = "alt_data.db"
TICKERS = ["NVDA", "TSLA", "AAPL", "PLTR", "QQQ", "SPY"]
LUXURY_TICKERS = {"LVMUY": "LVMH", "CFRUY": "Richemont", "SWGAY": "Swatch"}

# Load secrets from Environment Variables (GitHub Secrets)
AVIATION_API_KEY = os.environ.get("AVIATION_KEY", "DEMO_KEY_IF_MISSING")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK", "")

analyzer = SentimentIntensityAnalyzer()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS retail_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT, avg_sentiment REAL, bullish_count INTEGER, bearish_count INTEGER, total_posts INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS luxury_macro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT, company_name TEXT, price REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS aviation_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_active_flights INTEGER)''')
    conn.commit()
    conn.close()

def send_alert(message):
    """Sends a push notification to Discord if configured"""
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"🚨 **ALT-DATA ALERT:** {message}"})
    except Exception as e:
        print(f"Failed to send webhook: {e}")

def fetch_and_store_sentiment():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    headers = {'User-Agent': 'python:alt-data-pipeline', 'Accept': 'application/json'}
    
    for ticker in TICKERS:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                messages = response.json().get('messages', [])
                if not messages: continue
                
                scores = [analyzer.polarity_scores(msg.get('body', ''))['compound'] for msg in messages if msg.get('body')]
                bullish = sum(1 for s in scores if s >= 0.05)
                bearish = sum(1 for s in scores if s <= -0.05)
                        
                if scores:
                    avg_sentiment = sum(scores) / len(scores)
                    cursor.execute('''INSERT INTO retail_sentiment (ticker, avg_sentiment, bullish_count, bearish_count, total_posts)
                                      VALUES (?, ?, ?, ?, ?)''', (ticker, avg_sentiment, bullish, bearish, len(scores)))
                    print(f"[{datetime.now()}] Saved Sentiment for {ticker}: Avg={avg_sentiment:.2f}")
                    
                    # Anomaly Detection Logic
                    if avg_sentiment <= -0.50:
                        send_alert(f"${ticker} sentiment has collapsed to {avg_sentiment:.2f}! Retail panic detected.")
                    elif avg_sentiment >= 0.50:
                        send_alert(f"${ticker} sentiment has spiked to {avg_sentiment:.2f}! Extreme retail euphoria.")
                        
        except Exception as e:
            print(f"Error fetching StockTwits for {ticker}: {e}")
    conn.commit()
    conn.close()

def fetch_and_store_macro():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for ticker, name in LUXURY_TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                cursor.execute('INSERT INTO luxury_macro (ticker, company_name, price) VALUES (?, ?, ?)', (ticker, name, price))
                print(f"[{datetime.now()}] Saved Macro for {name}: Price={price:.2f}")
        except Exception as e:
            pass
    conn.commit()
    conn.close()

def fetch_and_store_aviation():
    if AVIATION_API_KEY == "DEMO_KEY_IF_MISSING":
        print("Skipping Aviation data: No API key configured in environment variables.")
        return
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    url = f"http://api.aviationstack.com/v1/flights?access_key={AVIATION_API_KEY}&limit=100&flight_status=active"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            total_flights = response.json().get('pagination', {}).get('total', 0)
            cursor.execute('INSERT INTO aviation_activity (total_active_flights) VALUES (?)', (total_flights,))
            print(f"[{datetime.now()}] Saved Aviation Data: Total Active={total_flights}")
    except Exception as e:
        pass
    conn.commit()
    conn.close()

def export_to_csv():
    """Reads the SQLite database and exports tables to CSV for Excel analysts"""
    print("Exporting database to CSV files...")
    conn = sqlite3.connect(DB_NAME)
    try:
        pd.read_sql("SELECT * FROM retail_sentiment", conn).to_csv("retail_sentiment.csv", index=False)
        pd.read_sql("SELECT * FROM luxury_macro", conn).to_csv("luxury_macro.csv", index=False)
        pd.read_sql("SELECT * FROM aviation_activity", conn).to_csv("aviation_activity.csv", index=False)
        print("CSV export complete.")
    except Exception as e:
        print(f"CSV Export failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting Automated Alternative Data Pipeline...")
    init_db()
    print(f"\n--- Running Pipeline Batch at {datetime.now()} ---")
    fetch_and_store_sentiment()
    fetch_and_store_macro()
    fetch_and_store_aviation()
    
    export_to_csv()
    print("Batch complete. Exiting script. (GitHub Actions will re-run this next hour)")
