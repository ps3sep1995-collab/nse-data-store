import os
import glob
import pandas as pd

def get_fo_stock_list():
    """NSE F&O स्टॉक्स की लिस्ट (बिना ऑनलाइन रिक्वेस्ट के)"""
    fo_stocks = {
        'AARTIIND', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ACC', 'ADANIENT', 'ADANIPORTS', 
        'ALKEM', 'AMBUJACEMENT', 'APOLLOHOSP', 'APOLLOTYRE', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL', 
        'ATUL', 'AUBANK', 'AUROPHARMA', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJFINANCE', 
        'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BATAINDIA', 'BEL', 'BERGEPAINT', 
        'BHARATFORG', 'BHARTIARTL', 'BHEL', 'BIOCON', 'BSOFT', 'BPCL', 'BRITANNIA', 'BOSCHLTD', 
        'CANBK', 'CANFINHOME', 'CHAMBLFERT', 'CHOLAFIN', 'CIPLA', 'COALINDIA', 'COFORGE', 
        'COLPAL', 'CONCOR', 'COROMANDEL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'CYIENT', 'DABUR', 
        'DALBHARAT', 'DEEPACNTR', 'DIVISLAB', 'DIXON', 'DLF', 'DRREDDY', 'EICHERMOT', 'ESCORTS', 
        'EXIDEIND', 'FEDERALBNK', 'FACT', 'GAIL', 'GLENMARK', 'GMRINFRA', 'GNFC', 'GODREJCP', 
        'GODREJPROP', 'GRANULES', 'GRASIM', 'GUJGASLTD', 'HAL', 'HAVELLS', 'HCLTECH', 'HDFCAMC', 
        'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HAL', 'HINDCOPPER', 'HINDPETRO', 
        'HINDUNILVR', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA', 'IDFCFIRSTB', 'IEX', 'IGL', 
        'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'IOC', 
        'IPCALAB', 'IRCTC', 'IREDA', 'IRFC', 'ITC', 'JINDALSTEL', 'JKCEMENT', 'JSWSTEEL', 
        'JUBLFOOD', 'KEI', 'KALYANKJIL', 'KOTAKBANK', 'LALPATHLAB', 'LT', 'LTIM', 'LTF', 'LTSH', 
        'LUPIN', 'M&M', 'M&MFIN', 'MANAPPURAM', 'MARICO', 'MARUTI', 'MCX', 'METROPOLIS', 'MFSL', 
        'MGL', 'MOTHERSON', 'MPHASIS', 'MRF', 'MUTHOOTFIN', 'NATIONALUM', 'NAVINFLUOR', 'NCC', 
        'NESTLEIND', 'NMDC', 'NTPC', 'OBEROIRLTY', 'OFSS', 'OIL', 'ONGC', 'PAGEIND', 'PERSISTENT', 
        'PETRONET', 'PFC', 'PIDILITIND', 'PIIND', 'PNB', 'POLYCAB', 'POWERTGRID', 'PVRINOX', 
        'RAMCOCEM', 'RBLBANK', 'RECLTD', 'RELIANCE', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN', 
        'SHREECEM', 'SHRIRAMFIN', 'SIEMENS', 'SJVN', 'SRF', 'SUNPHARMA', 'SUNTV', 'SYNGENE', 
        'TATACHEMICALS', 'TATACOMM', 'TATACONSUM', 'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 
        'TCS', 'TECHM', 'TITAN', 'TORNTPHARM', 'TRENT', 'TVSMOTOR', 'UBL', 'ULTRACEMCO', 'UPL', 
        'VEDL', 'VOLTAS', 'WIPRO', 'YESBANK', 'ZEEL'
    }
    return fo_stocks

def process_existing_data():
    fo_stocks = get_fo_stock_list()
    print(f"✅ कुल {len(fo_stocks)} F&O स्टॉक्स की लिस्ट लोड हो गई।")

    data_folder = "data"
    output_folder = "stocks"
    os.makedirs(output_folder, exist_ok=True)

    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    print(f"📂 `data/` फ़ोल्डर में मौजूद {len(csv_files)} फ़ाइलों को प्रोसेस किया जा रहा है...")

    all_data = []

    for file in csv_files:
        date_str = os.path.basename(file).replace(".csv", "")
        try:
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
