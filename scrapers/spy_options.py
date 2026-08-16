import sqlite3
import yfinance as yf
from datetime import datetime

def fetch_and_store_spy_options(db_name="alt_data.db"):
    print("Running SPY Options Scraper...")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''CREATE TABLE IF NOT EXISTS spy_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            expiration_date TEXT,
            call_volume INTEGER,
            put_volume INTEGER,
            call_open_interest INTEGER,
            put_open_interest INTEGER,
            put_call_ratio REAL)''')
            
    try:
        spy = yf.Ticker('SPY')
        dates = spy.options
        
        # We want the nearest 2 expirations (typically 0DTE and 1DTE/2DTE)
        target_dates = dates[:2]
        
        for date in target_dates:
            opt = spy.option_chain(date)
            calls = opt.calls
            puts = opt.puts
            
            call_vol = int(calls['volume'].sum())
            put_vol = int(puts['volume'].sum())
            
            call_oi = int(calls['openInterest'].sum())
            put_oi = int(puts['openInterest'].sum())
            
            pcr = put_vol / call_vol if call_vol > 0 else 0
            
            cursor.execute('''INSERT INTO spy_options (
                                expiration_date, call_volume, put_volume, 
                                call_open_interest, put_open_interest, put_call_ratio
                              ) VALUES (?, ?, ?, ?, ?, ?)''', 
                           (date, call_vol, put_vol, call_oi, put_oi, pcr))
            
            print(f"[{datetime.now()}] Saved SPY Options for {date}: PCR={pcr:.2f}")
            
    except Exception as e:
        print(f"Error fetching SPY options: {e}")
        
    conn.commit()
    conn.close()
