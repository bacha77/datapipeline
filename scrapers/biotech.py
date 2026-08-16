import sqlite3
import requests
from datetime import datetime

# We will track active Phase 3 trials for major biotech companies
TICKERS = ["PFE", "MRNA", "CRSP"]

def fetch_and_store_biotech(db_name="alt_data.db"):
    print("Running Biotech Scraper...")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''CREATE TABLE IF NOT EXISTS biotech_trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT,
            active_phase3_trials INTEGER)''')
    
    biotech_map = {"PFE": "Pfizer", "MRNA": "Moderna", "CRSP": "CRISPR"}
    for ticker in TICKERS:
        try:
            company_name = biotech_map[ticker]
            url = f"https://clinicaltrials.gov/api/v2/studies?query.sponsor={company_name}&filter.phase=PHASE3&filter.overallStatus=RECRUITING&pageSize=1"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                totalCount = data.get('totalCount', 0)
                
                cursor.execute('''INSERT INTO biotech_trials (ticker, active_phase3_trials)
                                  VALUES (?, ?)''', (ticker, totalCount))
                print(f"[{datetime.now()}] Saved Biotech Data for {ticker}: {totalCount} Active Phase 3 Trials")
        except Exception as e:
            print(f"Error fetching Biotech data for {ticker}: {e}")
            
    conn.commit()
    conn.close()
