import os
import requests
import pandas as pd

# NSE Request Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_live_nse_mapping():
    """NSE से F&O स्टॉक्स, इंडेक्स और सेक्टर डेटा लाइव फैच करना"""
    print("🔄 NSE से F&O लिस्ट, सेक्टर्स और इंडेक्स डेटा फैच किया जा रहा है...")
    
    sector_map = {}
    index_map = {}

    # NSE Sectoral & Major Indices to fetch
    indices = {
        "NIFTY 50": "Banking & Financials", # Auto mapped inside
        "NIFTY BANK": "Banking",
        "NIFTY IT": "IT",
        "NIFTY AUTO": "Auto",
        "NIFTY PHARMA": "Pharma",
        "NIFTY FMCG": "FMCG",
        "NIFTY METAL": "Metals",
        "NIFTY REALTY": "Realty",
        "NIFTY ENERGY": "Oil & Gas / Energy",
        "NIFTY MEDIA": "Media",
        "NIFTY INFRA": "Infrastructure",
        "NIFTY PSU BANK": "Banking"
    }

    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)

        for idx_name in indices.keys():
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={idx_name.replace(' ', '%20').replace('&', '%26')}"
            res = session.get(url, headers=HEADERS, timeout=10)
            
            if res.status_code == 200:
                data = res.json().get('data', [])
                for item in data:
                    sym = item.get('symbol', '').upper()
                    if sym and sym != idx_name:
                        # Index Mapping
                        if sym not in index_map:
                            index_map[sym] = set()
                        index_map[sym].add(idx_name)
                        index_map[sym].add("F&O")

                        # Sector Mapping
                        if sym not in sector_map and idx_name in indices:
                            sector_map[sym] = indices[idx_name]

    except Exception as e:
        print(f"⚠️ NSE API फैच में चेतावनी/त्रुटि: {e}. Default Mappings का उपयोग किया जाएगा।")

    return sector_map, index_map

def process_and_enrich_csv(filepath, symbol, sector_map, index_map):
    """CSV को पढ़ना, NSE से फैच किए गए सेक्टर्स जोड़ना, कैलकुलेशन करना और CSV अपडेट करना"""
    if not os.path.exists(filepath):
        return

    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip()

        required_cols = ['DELIV_QTY', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']
        if not all(col in df.columns for col in required_cols):
            return

        # OHLC Fallbacks
        for col in ['OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRICE']:
            alt_col = col.replace('_PRICE', '')
            if col not in df.columns and alt_col in df.columns:
                df[col] = df[alt_col]
            elif col not in df.columns:
                df[col] = df['CLOSE_PRICE']

        # Numeric Conversion
        num_cols = ['DELIV_QTY', 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values(by='Date', ascending=True).reset_index(drop=True)

        # 1. Price Change %
        if 'PREV_CLOSE' in df.columns:
            df['PREV_CLOSE'] = pd.to_numeric(df['PREV_CLOSE'], errors='coerce')
            df['PRICE_CHG_PCT'] = ((df['CLOSE_PRICE'] - df['PREV_CLOSE']) / df['PREV_CLOSE']) * 100
        else:
            prev_close = df['CLOSE_PRICE'].shift(1)
            df['PRICE_CHG_PCT'] = ((df['CLOSE_PRICE'] - prev_close) / prev_close) * 100
        df['PRICE_CHG_PCT'] = df['PRICE_CHG_PCT'].fillna(0.0).round(2)

        # 2. Dynamic Sector and Index Metadata from NSE
        sym_upper = symbol.upper()
        detected_sector = sector_map.get(sym_upper, "Others/Broad Market")
        detected_indices = list(index_map.get(sym_upper, ["F&O"]))

        df['SECTOR'] = detected_sector
        df['INDICES'] = ", ".join(detected_indices)

        # 3. Moving Averages Calculation
        df['AVG_DELIV_2D'] = df['DELIV_QTY'].shift(1).rolling(window=2).mean().fillna(0).astype(int)
        df['AVG_DELIV_5D'] = df['DELIV_QTY'].shift(1).rolling(window=5).mean().fillna(0).astype(int)
        df['AVG_DELIV_7D'] = df['DELIV_QTY'].shift(1).rolling(window=7).mean().fillna(0).astype(int)
        df['AVG_DELIV_10D'] = df['DELIV_QTY'].shift(1).rolling(window=10).mean().fillna(0).astype(int)

        # 4. Spike Ratios
        df['R2'] = (df['DELIV_QTY'] / df['AVG_DELIV_2D'].replace(0, 1)).round(2)
        df['R5'] = (df['DELIV_QTY'] / df['AVG_DELIV_5D'].replace(0, 1)).round(2)
        df['R7'] = (df['DELIV_QTY'] / df['AVG_DELIV_7D'].replace(0, 1)).round(2)
        df['R10'] = (df['DELIV_QTY'] / df['AVG_DELIV_10D'].replace(0, 1)).round(2)

        df['MAX_SPIKE'] = df[['R2', 'R5', 'R7', 'R10']].max(axis=1).round(2)
        df['IS_2X'] = (df['MAX_SPIKE'] >= 2.0).astype(int)

        # Updated Enriched CSV Export
        df.to_csv(filepath, index=False)
        print(f"✅ [{detected_sector}] - {symbol} CSV Updated!")

    except Exception as e:
        print(f"❌ Error updating CSV for {symbol}: {e}")

if __name__ == "__main__":
    stocks_dir = "stocks"
    os.makedirs(stocks_dir, exist_ok=True)

    # 1. Get Live Sector & Index Mapping from NSE
    sector_map, index_map = get_live_nse_mapping()

    # 2. Process all Stock CSVs dynamically
    csv_files = [f for f in os.listdir(stocks_dir) if f.endswith(".csv")]
    print(f"📊 कुल {len(csv_files)} स्टॉक्स प्रोसेस किए जा रहे हैं...")

    for file in csv_files:
        symbol = file.replace(".csv", "")
        process_and_enrich_csv(os.path.join(stocks_dir, file), symbol, sector_map, index_map)
