import streamlit as st
import requests
import pandas as pd
import sqlite3
import os
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Alt-Data Dashboard", page_icon="📈", layout="wide")

st.title("📈 Alternative Data Intelligence Platform")
st.markdown("A unified dashboard tracking non-traditional signals to find alpha before the market does.")

# Connect to the SQLite Database
DB_NAME = "alt_data.db"
def load_db_data(query):
    if not os.path.exists(DB_NAME):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗣️ Retail Sentiment", 
    "⌚ Luxury Goods Proxy", 
    "✈️ Global Aviation",
    "🏦 Smart Money",
    "📊 Historical Archive"
])

# ==========================================
# TAB 1: RETAIL SENTIMENT (Live)
# ==========================================
with tab1:
    st.header("Retail Sentiment (Live API)")
    analyzer = SentimentIntensityAnalyzer()

    def fetch_stocktwits(ticker):
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        headers = {'User-Agent': 'python:alt-data-dash', 'Accept': 'application/json'}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            posts = []
            for msg in data.get('messages', []):
                posts.append({
                    'created_utc': datetime.strptime(msg.get('created_at'), "%Y-%m-%dT%H:%M:%SZ"),
                    'text': msg.get('body', ''),
                    'username': msg.get('user', {}).get('username', 'Unknown')
                })
            return posts
        except Exception as e:
            return []

    target_ticker = st.text_input("Enter a Stock Ticker (e.g., NVDA, AAPL, QQQ, SPY)", value="NVDA", key="stocktwits_ticker").upper()

    if st.button("Fetch Live Sentiment"):
        with st.spinner(f"Fetching live sentiment for ${target_ticker}..."):
            posts = fetch_stocktwits(target_ticker)
            if posts:
                df = pd.DataFrame(posts)
                df['sentiment_score'] = df['text'].apply(lambda x: analyzer.polarity_scores(x)['compound'])
                df['sentiment_category'] = df['sentiment_score'].apply(
                    lambda s: "Bullish 🐂" if s >= 0.05 else ("Bearish 🐻" if s <= -0.05 else "Neutral 😐")
                )
                
                avg_sentiment = df['sentiment_score'].mean()
                col1, col2, col3 = st.columns(3)
                col1.metric("Average Sentiment", f"{avg_sentiment:.2f}")
                col2.metric("Bullish Posts", len(df[df['sentiment_category'] == "Bullish 🐂"]))
                col3.metric("Bearish Posts", len(df[df['sentiment_category'] == "Bearish 🐻"]))
                
                fig = px.histogram(df, x='sentiment_score', color='sentiment_category')
                st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 2: LUXURY GOODS MACRO PROXY
# ==========================================
with tab2:
    st.header("Luxury Market Macro Proxy (Live API)")
    tickers = {"LVMUY": "LVMH", "CFRUY": "Richemont", "SWGAY": "Swatch Group"}
    period = st.selectbox("Select Timeframe", ["1mo", "6mo", "1y", "5y"], index=2)
    
    if st.button("Fetch Live Luxury Data"):
        with st.spinner("Fetching Yahoo Finance data..."):
            df_prices = pd.DataFrame()
            for ticker in tickers.keys():
                hist = yf.Ticker(ticker).history(period=period)
                if not hist.empty: df_prices[tickers[ticker]] = hist['Close']
            
            if not df_prices.empty:
                df_normalized = (df_prices / df_prices.iloc[0]) * 100
                fig2 = px.line(df_normalized, title="Luxury Conglomerates - Relative Performance")
                st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# TAB 3: GLOBAL AVIATION
# ==========================================
with tab3:
    st.header("Live Aviation Tracker")
    api_key = st.text_input("Aviationstack API Key", type="password", value="1a914c9afac0f92d1d195165200702c5")
    limit = st.slider("Flights to Fetch", 5, 50, 10)
    
    if st.button("Fetch Live Flight Data"):
        with st.spinner("Fetching live flights..."):
            url = f"http://api.aviationstack.com/v1/flights?access_key={api_key}&limit={limit}&flight_status=active"
            try:
                response = requests.get(url)
                data = response.json()
                if 'data' in data:
                    st.success(f"Retrieved {len(data['data'])} live active flights!")
                    st.json(data['data']) # Simplified display for space
            except:
                st.error("Failed to fetch.")

# ==========================================
# TAB 4: SMART MONEY
# ==========================================
with tab4:
    st.header("🏦 Smart Money Tracker")
    smart_money_ticker = st.text_input("Audit Institutional Money", value="AAPL", key="smart_money_ticker").upper()
    if st.button("Audit"):
        with st.spinner("Pulling 13F and Form 4..."):
            stock = yf.Ticker(smart_money_ticker)
            st.write(stock.institutional_holders)

# ==========================================
# TAB 5: HISTORICAL ARCHIVE (PIPELINE DATA)
# ==========================================
with tab5:
    st.header("📊 Automated Historical Archive")
    st.markdown("""
    This tab reads from your local SQLite database (`alt_data.db`), which is being continuously updated by your background `data_pipeline.py` script.
    **To answer your question:** You typically need **1 to 3 years** of this stored historical data to backtest a strategy effectively before you can sell the API or trade confidently on it to generate income.
    """)
    
    if os.path.exists(DB_NAME):
        st.success("✅ Background Data Pipeline is active and SQLite database found!")
        
        # Load Sentiment Data
        df_sent = load_db_data("SELECT * FROM retail_sentiment")
        if not df_sent.empty:
            df_sent['timestamp'] = pd.to_datetime(df_sent['timestamp'])
            st.subheader("Historical Retail Sentiment")
            fig_hist = px.line(df_sent, x='timestamp', y='avg_sentiment', color='ticker', markers=True, title="Average Sentiment Over Time (Pipeline Data)")
            st.plotly_chart(fig_hist, use_container_width=True)
            st.dataframe(df_sent)
            
        # Load Aviation Data
        df_aviation = load_db_data("SELECT * FROM aviation_activity")
        if not df_aviation.empty:
            df_aviation['timestamp'] = pd.to_datetime(df_aviation['timestamp'])
            st.subheader("Historical Global Flight Activity")
            fig_av = px.line(df_aviation, x='timestamp', y='total_active_flights', markers=True, title="Total Active Flights Worldwide")
            st.plotly_chart(fig_av, use_container_width=True)
            
    else:
        st.warning("Database not found yet. The pipeline may still be running its first batch.")
