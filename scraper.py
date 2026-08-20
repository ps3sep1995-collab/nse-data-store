import requests
import datetime
import os
import pandas as pd
import io
import time

def fetch_last_month():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    os.makedirs("data", exist_ok=True)
    success_count = 0

    print("🚀 Fetching last 30 days data...")

    for days_back in range(0, 30):
        target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        date_str = target_date.strftime("%d%m%Y")
        file_date = target_date.strftime("%Y-%m-%d")
        
        output_path = f"data/{file_date}.csv"
        
        # फ़ाइल पहले से है तो स्किप करें
        if os.path.exists(output_path):
            print(f"⏩ Already exists: {file_date}")
            continue

        url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200 and len(response.content) > 1000:
                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                df.columns = df.columns.str.strip()

                if 'SERIES' in df.columns:
                    df = df[df['SERIES'].str.strip() == 'EQ']

                df.to_csv(output_path, index=False)
                print(f"✅ Downloaded: {file_date}")
                success_count += 1
            else:
                print(f"⏩ Skipped: {file_date}")
        except Exception as e:
            print(f"⚠️ Error on {file_date}: {e}")

        # NSE सर्वर ब्लॉक न करे इसलिए 1 सेकंड की देरी
        time.sleep(1)

    print(f"\n🎉 Finished! Processed successfully.")

if __name__ == "__main__":
    fetch_last_month()
