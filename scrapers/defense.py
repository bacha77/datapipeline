import sqlite3
import requests
from datetime import datetime

# USASpending API endpoint for contract awards
API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Mapping Defense/Tech companies to their common keywords in federal contracts
DEFENSE_COMPANIES = {
    "PLTR": "PALANTIR",
    "LMT": "LOCKHEED MARTIN",
    "RTX": "RAYTHEON"
}

def fetch_and_store_defense(db_name="alt_data.db"):
    print("Running Defense Contracts Scraper...")
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute('''CREATE TABLE IF NOT EXISTS defense_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ticker TEXT,
            total_awarded_amount REAL)''')
            
    headers = {"Content-Type": "application/json"}
    
    for ticker, keyword in DEFENSE_COMPANIES.items():
        try:
            # Payload to search for recent huge contracts
            payload = {
                "filters": {
                    "award_type_codes": ["A", "B", "C", "D"], # Contracts
                    "recipient_search_text": [keyword],
                    "time_period": [{"date_type": "action_date", "start_date": "2024-01-01", "end_date": "2026-12-31"}]
                },
                "fields": ["Award Amount"],
                "limit": 100,
                "sort": "Award Amount",
                "order": "desc"
            }
            response = requests.post(API_URL, json=payload, headers=headers)
            if response.status_code == 200:
                results = response.json().get('results', [])
                total_amount = sum(float(r.get('Award Amount', 0) or 0) for r in results)
                
                cursor.execute('''INSERT INTO defense_contracts (ticker, total_awarded_amount)
                                  VALUES (?, ?)''', (ticker, total_amount))
                print(f"[{datetime.now()}] Saved Defense Data for {ticker}: ${total_amount:,.2f} Total Awards")
        except Exception as e:
            print(f"Error fetching Defense data for {ticker}: {e}")
            
    conn.commit()
    conn.close()
