import sqlite3
import requests
import time
import yfinance as yf
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Configuration
DB_NAME = "alt_data.db"
TICKERS = ["NVDA", "TSLA", "AAPL", "PLTR", "QQQ", "SPY"]
LUXURY_TICKERS = {"LVMUY": "LVMH", "CFRUY": "Richemont", "SWGAY": "Swatch"}
AVIATION_API_KEY = "1a914c9afac0f92d1d195165200702c5"
POLL_INTERVAL_SECONDS = 3600 # Run every 1 hour

analyzer = SentimentIntensityAnalyzer()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Retail Sentiment Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS retail_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT,
            avg_sentiment REAL,
            bullish_count INTEGER,
            bearish_count INTEGER,
            total_posts INTEGER
        )
    ''')
    
    # Luxury Macro Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS luxury_macro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT,
            company_name TEXT,
            price REAL
        )
    ''')
    
    # Aviation Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aviation_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_active_flights INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

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
                if not messages:
                    continue
                
                scores = []
                bullish = 0
                bearish = 0
                
                for msg in messages:
                    text = msg.get('body', '')
                    if text:
                        score = analyzer.polarity_scores(text)['compound']
                        scores.append(score)
                        if score >= 0.05: bullish += 1
                        elif score <= -0.05: bearish += 1
                        
                if scores:
                    avg_sentiment = sum(scores) / len(scores)
                    cursor.execute('''
                        INSERT INTO retail_sentiment (ticker, avg_sentiment, bullish_count, bearish_count, total_posts)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (ticker, avg_sentiment, bullish, bearish, len(scores)))
                    print(f"[{datetime.now()}] Saved Sentiment for {ticker}: Avg={avg_sentiment:.2f}")
        except Exception as e:
            print(f"Error fetching StockTwits for {ticker}: {e}")
            
    conn.commit()
    conn.close()

def fetch_and_store_macro():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for ticker, name in LUXURY_TICKERS.items():
        try:
            stock = yf.Ticker(ticker)
            # Fast fetch for current price
            hist = stock.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                cursor.execute('''
                    INSERT INTO luxury_macro (ticker, company_name, price)
                    VALUES (?, ?, ?)
                ''', (ticker, name, price))
                print(f"[{datetime.now()}] Saved Macro for {name}: Price={price:.2f}")
        except Exception as e:
            print(f"Error fetching Macro for {ticker}: {e}")
            
    conn.commit()
    conn.close()

def fetch_and_store_aviation():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    url = f"http://api.aviationstack.com/v1/flights?access_key={AVIATION_API_KEY}&limit=100&flight_status=active"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Pagination object has total active flights
            total_flights = data.get('pagination', {}).get('total', 0)
            cursor.execute('''
                INSERT INTO aviation_activity (total_active_flights)
                VALUES (?)
            ''', (total_flights,))
            print(f"[{datetime.now()}] Saved Aviation Data: Total Active={total_flights}")
    except Exception as e:
        print(f"Error fetching Aviation data: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Starting Automated Alternative Data Pipeline...")
    init_db()
    
    print(f"\n--- Running Pipeline Batch at {datetime.now()} ---")
    fetch_and_store_sentiment()
    fetch_and_store_macro()
    fetch_and_store_aviation()
    print("Batch complete. Exiting script. (GitHub Actions will re-run this next hour)")
