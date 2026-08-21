import os
import glob
import pandas as pd
import requests
import io

def get_fo_stock_list():
    """NSE से F&O स्टॉक्स की लिस्ट फेच करना (Encoding Fix के साथ)"""
    url = "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    fo_stocks = set()
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # latin1 / cp1252 डिकोडिंग एरर से बचाव के लिए
            content = response.content.decode('latin1')
            df = pd.read_csv(io.StringIO(content))
            df.columns = df.columns.str.strip()
            
            if 'UNDERLYING' in df.columns:
                symbols = df['UNDERLYING'].astype(str).str.strip().unique()
                indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYNEXT50']
                fo_stocks = {s for s in symbols if s not in indices and s != 'nan'}
                print(f"✅ कुल {len(fo_stocks)} F&O स्टॉक्स की लिस्ट मिल गई।")
    except Exception as e:
        print(f"⚠️ F&O लिस्ट प्राप्त करने में त्रुटि: {e}")
    
    return fo_stocks

def process_existing_data():
    fo_stocks = get_fo_stock_list()
    
    if not fo_stocks:
        print("❌ F&O लिस्ट प्राप्त नहीं हुई, प्रोसेस रोका गया।")
        return

    data_folder = "data"
    output_folder = "stocks"
    os.makedirs(output_folder, exist_ok=True)

    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    print(f"📂 `data/` फ़ोल्डर में मौजूद {len(csv_files)} फ़ाइलों को प्रोसेस किया जा रहा है...")

    all_data = []

    for file in csv_files:
        date_str = os.path.basename(file).replace(".csv", "")
        try:
            # encoding_errors ignore करके फ़ाइल आसानी से पढ़ें
            df = pd.read_csv(file, encoding='latin1', on_bad_lines='skip')
            df.columns = df.columns.str.strip()
            
            if 'SERIES' in df.columns:
                df = df[df['SERIES'].astype(str).str.strip() == 'EQ']

            if 'SYMBOL' in df.columns:
                df['SYMBOL'] = df['SYMBOL'].astype(str).str.strip()
                df = df[df['SYMBOL'].isin(fo_stocks)].copy()
                df['Date'] = date_str
                all_data.append(df)
        except Exception as e:
            pass

    if not all_data:
        print("❌ `data/` फ़ोल्डर में कोई F&O Equity डेटा नहीं मिला।")
        return

    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df['Date'] = pd.to_datetime(combined_df['Date'])
    combined_df = combined_df.sort_values(by='Date', ascending=True)

    grouped = combined_df.groupby('SYMBOL')
    saved_count = 0

    for symbol, group in grouped:
        group['Date'] = group['Date'].dt.strftime('%Y-%m-%d')
        cols = ['Date'] + [col for col in group.columns if col != 'Date']
        stock_df = group[cols]

        output_path = os.path.join(output_folder, f"{symbol}.csv")
        stock_df.to_csv(output_path, index=False)
        saved_count += 1

    print(f"\n🎉 सफलता! `stocks/` फ़ोल्डर में कुल {saved_count} स्टॉक्स की फ़ाइलें बन गईं।")

if __name__ == "__main__":
    process_existing_data()
