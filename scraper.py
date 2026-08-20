import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_clean_data(days_to_fetch=250):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    os.makedirs("data", exist_ok=True)
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    for days_back in range(0, days_to_fetch):
        target_date = now_ist - datetime.timedelta(days=days_back)
        
        # 1. शनिवार (5) और रविवार (6) सीधे बाहर
        if target_date.weekday() >= 5:
            continue

        file_date = target_date.strftime("%Y-%m-%d") # उदाहरण: 2026-08-20
        date_str = target_date.strftime("%d%m%Y")
        output_path = f"data/{file_date}.csv"

        if os.path.exists(output_path):
            continue

        url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            # अगर सर्वर पर फ़ाइल 200 OK देती है
            if response.status_code == 200 and len(response.content) > 2000:
                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                df.columns = df.columns.str.strip()

                # 2. HOLIDAY CHECK (Dynamic Matching):
                # NSE छुट्टी के दिन पुरानी फ़ाइल भेजता है, तो CSV में लिखी असली तारीख (DATE1) मैच करें
                if 'DATE1' in df.columns:
                    actual_csv_date = pd.to_datetime(df['DATE1'].iloc[0]).strftime("%Y-%m-%d")
                    
                    # अगर डाउनलोड की गई तारीख और CSV के अंदर लिखी तारीख अलग है -> तो वह छुट्टी का दिन है!
                    if actual_csv_date != file_date:
                        print(f"⏩ Skipped Holiday (CSV Date mismatch): {file_date}")
                        continue

                if 'SERIES' in df.columns:
                    df = df[df['SERIES'].str.strip() == 'EQ']

                # 3. अगर शेयर मार्केट खुला था तो ट्रेड वॉल्यूम 0 नहीं होगा
                if len(df) > 500:
                    df.to_csv(output_path, index=False)
                    print(f"✅ Clean Market Day Saved: {file_date}")
        except Exception as e:
            pass

        time.sleep(1)

if __name__ == "__main__":
    fetch_clean_data(250)
