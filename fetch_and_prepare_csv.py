import os
import pandas as pd

def fix_and_enrich_all_csvs():
    stocks_dir = "stocks"
    if not os.path.exists(stocks_dir):
        print("❌ `stocks` फ़ोल्डर नहीं मिला!")
        return

    csv_files = [f for f in os.listdir(stocks_dir) if f.endswith(".csv")]
    print(f"🔄 कुल {len(csv_files)} CSV फ़ाइलों को री-प्रोसेस किया जा रहा है...")

    for file in csv_files:
        filepath = os.path.join(stocks_dir, file)
        try:
            df = pd.read_csv(filepath)
            df.columns = df.columns.str.strip().str.upper()

            # Fix Column Names
            col_map = {'CLOSE': 'CLOSE_PRICE', 'OPEN': 'OPEN_PRICE', 'HIGH': 'HIGH_PRICE', 'LOW': 'LOW_PRICE', 'DELIVERY': 'DELIV_QTY'}
            df.rename(columns=col_map, inplace=True)

            if 'CLOSE_PRICE' not in df.columns or 'DELIV_QTY' not in df.columns:
                continue

            # Ensure Numeric Data
            num_cols = ['CLOSE_PRICE', 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'DELIV_QTY', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            df = df.sort_values(by='Date', ascending=True).reset_index(drop=True)

            # Calculate Previous Close
            df['PREV_CLOSE'] = df['CLOSE_PRICE'].shift(1)
            df['PREV_CLOSE'] = df['PREV_CLOSE'].fillna(df['OPEN_PRICE'])

            # Calculate Price Change %
            df['PRICE_CHG_PCT'] = ((df['CLOSE_PRICE'] - df['PREV_CLOSE']) / df['PREV_CLOSE'].replace(0, 1)) * 100
            df['PRICE_CHG_PCT'] = df['PRICE_CHG_PCT'].round(2)

            # Averages & Spikes
            df['AVG_DELIV_2D'] = df['DELIV_QTY'].shift(1).rolling(2).mean().fillna(0)
            df['AVG_DELIV_5D'] = df['DELIV_QTY'].shift(1).rolling(5).mean().fillna(0)
            df['AVG_DELIV_7D'] = df['DELIV_QTY'].shift(1).rolling(7).mean().fillna(0)
            df['AVG_DELIV_10D'] = df['DELIV_QTY'].shift(1).rolling(10).mean().fillna(0)

            df['R2'] = (df['DELIV_QTY'] / df['AVG_DELIV_2D'].replace(0, 1)).round(2)
            df['R5'] = (df['DELIV_QTY'] / df['AVG_DELIV_5D'].replace(0, 1)).round(2)
            df['R7'] = (df['DELIV_QTY'] / df['AVG_DELIV_7D'].replace(0, 1)).round(2)
            df['R10'] = (df['DELIV_QTY'] / df['AVG_DELIV_10D'].replace(0, 1)).round(2)

            df['MAX_SPIKE'] = df[['R2', 'R5', 'R7', 'R10']].max(axis=1).round(2)
            df['IS_2X'] = (df['MAX_SPIKE'] >= 2.0).astype(int)

            df.to_csv(filepath, index=False)
        except Exception as e:
            print(f"Error in {file}: {e}")

    print("✅ सभी CSV फ़ाइलें सफलतापूर्वक अपडेट हो गईं!")

if __name__ == "__main__":
    fix_and_enrich_all_csvs()
