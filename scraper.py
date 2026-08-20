import requests
import datetime
import os
import pandas as pd
import io

def fetch_and_process():
    today = datetime.datetime.now()
    date_str = today.strftime("%d%m%Y")
    file_date = today.strftime("%Y-%m-%d")

    url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200 and len(response.content) > 1000:
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            df.columns = df.columns.str.strip()

            if 'SERIES' in df.columns:
                df = df[df['SERIES'].str.strip() == 'EQ']

            os.makedirs("data", exist_ok=True)
            output_path = f"data/{file_date}.csv"
            df.to_csv(output_path, index=False)
            print(f"✅ Data saved: {output_path}")
        else:
            print(f"⚠️ No data for {file_date} (Market Holiday / Weekend)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fetch_and_process()

