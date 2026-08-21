import os
import glob
import pandas as pd
import requests
import io

def get_fo_stock_list():
    """NSE की आधिकारिक लिस्ट से केवल F&O स्टॉक्स के सिंबल निकालना"""
    url = "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    fo_stocks = set()
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            df.columns = df.columns.str.strip()
            
            # UNDERLYING कॉलम से स्टॉक्स के नाम निकालना
            if 'UNDERLYING' in df.columns:
                symbols = df['UNDERLYING'].str.strip().unique()
                # केवल स्टॉक्स रखें, इंडेक्स (NIFTY, BANKNIFTY) को हटा दें
                indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYNEXT50']
                fo_stocks = {s for s in symbols if s not in indices}
                print(f"✅ कुल {len(fo_stocks)} F&O स्टॉक्स की लिस्ट मिल गई है।")
    except Exception as e:
        print(f"⚠️ F&O लिस्ट प्राप्त करने में समस्या: {e}")
    
    return fo_stocks

def process_and_split():
    fo_stocks = get_fo_stock_list()
    
    if not fo_stocks:
        print("❌ F&O लिस्ट प्राप्त नहीं हो सकी। प्रोसेस रोका गया।")
        return

    data_folder = "data"
    output_folder = "stocks"
    os.makedirs(output_folder, exist_ok=True)

    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    print(f"📂 `data/` फ़ोल्डर की कुल {len(csv_files)} फ़ाइलों को स्कैन किया जा रहा है...")

    all_data = []

    for file in csv_files:
        date_str = os.path.basename(file).replace(".csv", "")
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()
            
            # 1. केवल Equity (EQ) सीरीज़ फ़िल्टर करें
            if 'SERIES' in df.columns:
                df = df[df['SERIES'].str.strip() == 'EQ']

            # 2. केवल वही स्टॉक्स रखें जो F&O की लिस्ट में मौजूद हैं
            if 'SYMBOL' in df.columns:
                df['SYMBOL'] = df['SYMBOL'].str.strip()
                df = df[df['SYMBOL'].isin(fo_stocks)].copy()
                df['Date'] = date_str
                all_data.append(df)
        except Exception as e:
            pass

    if not all_data:
        print("❌ कोई मैचिंग डेटा नहीं मिला।")
        return

    # सारा डेटा एक साथ कंबाइन करना
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df['Date'] = pd.to_datetime(combined_df['Date'])
    combined_df = combined_df.sort_values(by='Date', ascending=True)

    # हर F&O Equity स्टॉक की अलग CSV फ़ाइल बनाना
    grouped = combined_df.groupby('SYMBOL')
    saved_count = 0

    for symbol, group in grouped:
        group['Date'] = group['Date'].dt.strftime('%Y-%m-%d')
        cols = ['Date'] + [col for col in group.columns if col != 'Date']
        stock_df = group[cols]

        output_path = os.path.join(output_folder, f"{symbol}.csv")
        stock_df.to_csv(output_path, index=False)
        saved_count += 1

    print(f"\n🎉 सफलता! `stocks/` फ़ोल्डर में कुल {saved_count} F&O Equity स्टॉक्स की फ़ाइलें बन गईं।")

if __name__ == "__main__":
    process_and_split()
