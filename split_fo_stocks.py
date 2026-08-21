import os
import glob
import pandas as pd
import requests
import io

def get_fo_stock_list():
    """NSE से F&O में ट्रेड होने वाले स्टॉक्स की लिस्ट डाउनलोड करना"""
    url = "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    fo_stocks = set()
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            df.columns = df.columns.str.strip()
            if 'UNDERLYING' in df.columns:
                # NIFTY, BANKNIFTY इंडेक्स को हटाकर सिर्फ इक्विटी स्टॉक्स रखें
                symbols = df['UNDERLYING'].str.strip().unique()
                fo_stocks = {s for s in symbols if s not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY']}
                print(f"✅ कुल {len(fo_stocks)} F&O स्टॉक्स मिले।")
    except Exception as e:
        print(f"⚠️ F&O लिस्ट प्राप्त करने में त्रुटि: {e}")
    
    return fo_stocks

def process_and_split_data():
    fo_stocks = get_fo_stock_list()
    
    if not fo_stocks:
        print("❌ F&O लिस्ट नहीं मिल पाई, प्रोसेस रोक दिया गया है।")
        return

    data_folder = "data"
    output_folder = "stocks"
    os.makedirs(output_folder, exist_ok=True)

    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    print(f"📂 कुल {len(csv_files)} डेली CSV फ़ाइलों को प्रोसेस किया जा रहा है...")

    all_fo_data = []

    # 1. सभी Daily Files को पढ़ना और Filter करना
    for file in csv_files:
        date_str = os.path.basename(file).replace(".csv", "")
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()
            
            if 'SYMBOL' in df.columns:
                df['SYMBOL'] = df['SYMBOL'].str.strip()
                # केवल F&O वाले स्टॉक्स को फ़िल्टर करना (Non-F&O Removed)
                fo_df = df[df['SYMBOL'].isin(fo_stocks)].copy()
                fo_df['Date'] = date_str
                all_fo_data.append(fo_df)
        except Exception as e:
            pass

    if not all_fo_data:
        print("❌ कोई F&O डेटा नहीं मिला।")
        return

    # 2. पूरा F&O डेटा एक साथ मिलाना
    combined_df = pd.concat(all_fo_data, ignore_index=True)
    combined_df['Date'] = pd.to_datetime(combined_df['Date'])
    combined_df = combined_df.sort_values(by='Date', ascending=True)

    # 3. हर स्टॉक की अपनी अलग CSV फ़ाइल बनाना
    grouped = combined_df.groupby('SYMBOL')
    saved_count = 0

    for symbol, group in grouped:
        # तारीख़ को साफ़ फ़ॉर्मेट में वापस सेट करना
        group['Date'] = group['Date'].dt.strftime('%Y-%m-%d')
        
        # 'Date' कॉलम को सबसे आगे रखना
        cols = ['Date'] + [col for col in group.columns if col != 'Date']
        stock_df = group[cols]

        output_path = os.path.join(output_folder, f"{symbol}.csv")
        stock_df.to_csv(output_path, index=False)
        saved_count += 1

    print(f"\n🎉 सफलता! 'stocks/' फ़ोल्डर में कुल {saved_count} F&O स्टॉक्स की अलग-अलग फ़ाइलें बन गईं।")

if __name__ == "__main__":
    process_and_split_data()
