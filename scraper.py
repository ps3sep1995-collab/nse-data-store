import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_10_years_data(days_to_fetch=2500): # 2500 days = ~10 Years
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    os.makedirs("data", exist_ok=True)
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 पिछले 10 साल ({days_to_fetch} दिन) का डेटा डाउनलोड होना शुरू हो रहा है...")

    success_count = 0

    for days_back in range(0, days_to_fetch):
        target_date = now_ist - datetime.timedelta(days=days_back)
        
        # शनिवार (5) और रविवार (6) सीधे बाहर
        if target_date.weekday() >= 5:
            continue

        file_date = target_date.strftime("%Y-%m-%d") # उदाहरण: 2016-08-20
        date_str = target_date.strftime("%d%m%Y")
        output_path = f"data/{file_date}.csv"

        # अगर फ़ाइल पहले से डाउनलोड है तो दोबारा न करें
        if os.path.exists(output_path):
            continue

        url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"

        try:
            response = requests.get(url, headers=headers, timeout=12)
            
            if response.status_code == 200 and len(response.content) > 2000:
                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                df.columns = df.columns.str.strip()

                # Holiday Check (DATE1 Match)
                if 'DATE1' in df.columns:
                    actual_csv_date = pd.to_datetime(df['DATE1'].iloc[0]).strftime("%Y-%m-%d")
                    if actual_csv_date != file_date:
                        print(f"⏩ Skipped Holiday: {file_date}")
                        continue

                if 'SERIES' in df.columns:
                    df = df[df['SERIES'].str.strip() == 'EQ']

                if len(df) > 300:
                    df.to_csv(output_path, index=False)
                    success_count += 1
                    print(f"✅ Saved ({success_count}): {file_date}")
            else:
                print(f"⏩ No Data / Closed: {file_date}")
        except Exception as e:
            print(f"⚠️ Error on {file_date}: {e}")

        # NSE Blocks रोखने के लिए 0.8 से 1 सेकंड का गैप रखें
        time.sleep(0.8)

    print(f"\n🎉 10 साल का डाउनलोड पूरा! कुल {success_count} फ़ाइलें सेव हुईं।")

if __name__ == "__main__":
    fetch_10_years_data(2500)
