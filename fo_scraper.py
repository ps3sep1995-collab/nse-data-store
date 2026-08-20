import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_fo_data(days_to_fetch=10):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': '*/*'
    }
    
    output_folder = "fo_data"
    os.makedirs(output_folder, exist_ok=True)
    
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 F&O Data Fetching Started (Last {days_to_fetch} Days)...")

    for days_back in range(0, days_to_fetch):
        target_date = now_ist - datetime.timedelta(days=days_back)
        
        # वीकेंड (शनिवार/रविवार) को स्किप करें
        if target_date.weekday() >= 5:
            continue

        file_date = target_date.strftime("%Y-%m-%d")
        output_path = os.path.join(output_folder, f"{file_date}_FO.csv")

        if os.path.exists(output_path):
            print(f"⏩ F&O File Already Exists: {file_date}")
            continue

        date_str_upper = target_date.strftime("%d%b%Y").upper() # उदा: 20AUG2026
        month_str_upper = target_date.strftime("%b").upper()     # उदा: AUG
        year_str = target_date.strftime("%Y")                    # उदा: 2026
        
        # NSE F&O URLs (Primary & Alternative)
        urls = [
            f"https://archives.nseindia.com/content/historical/DERIVATIVES/{year_str}/{month_str_upper}/fo{date_str_upper}bhav.csv.zip",
            f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{year_str}/{month_str_upper}/fo{date_str_upper}bhav.csv.zip"
        ]

        downloaded = False
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200 and len(response.content) > 1000:
                    df = pd.read_csv(io.BytesIO(response.content), compression='zip')
                    df.columns = df.columns.str.strip()

                    if 'SYMBOL' in df.columns:
                        df.to_csv(output_path, index=False)
                        print(f"✅ F&O Data Saved: {file_date}")
                        downloaded = True
                        break
            except Exception as e:
                pass

        if not downloaded:
            print(f"⏩ Market Closed / No F&O Data: {file_date}")

        time.sleep(0.8)

if __name__ == "__main__":
    fetch_fo_data(10)
