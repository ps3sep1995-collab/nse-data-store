import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_all_days_data(days_to_fetch=5000):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    os.makedirs("data", exist_ok=True)
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)

    print(f"🚀 Saturday/Sunday Check Included: Checking last {days_to_fetch} days...")

    for days_back in range(0, days_to_fetch):
        target_date = now_ist - datetime.timedelta(days=days_back)
        
        file_date = target_date.strftime("%Y-%m-%d") # उदा: 2026-08-20
        date_str = target_date.strftime("%d%m%Y")    # उदा: 20082026
        output_path = f"data/{file_date}.csv"

        # अगर फ़ाइल पहले से डाउनलोड है तो दोबारा न करें
        if os.path.exists(output_path):
            continue

        url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"

        try:
            response = requests.get(url, headers=headers, timeout=8)
            
            # अगर NSE सर्वर ने उस तारीख़ का डेटा दिया (200 OK)
            if response.status_code == 200 and len(response.content) > 2000:
                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                df.columns = df.columns.str.strip()

                # 1. HOLIDAY & WEEKEND CHECK via DATE1:
                # NSE छुट्टी या वीकेंड के दिन पुरानी फ़ाइल वापस भेजता है।
                if 'DATE1' in df.columns:
                    actual_csv_date = pd.to_datetime(df['DATE1'].iloc[0]).strftime("%Y-%m-%d")
                    
                    # अगर डाउनलोड की गई तारीख़ और CSV के अंदर की असली तारीख़ मैच नहीं करती -> इसका मतलब मार्केट बंद था
                    if actual_csv_date != file_date:
                        continue

                # 2. Equity Segment Filter
                if 'SERIES' in df.columns:
                    df = df[df['SERIES'].str.strip() == 'EQ']

                # 3. अगर स्टॉक की संख्या 300 से ज़्यादा है, यानी उस दिन ट्रेडिंग हुई थी!
                if len(df) > 300:
                    df.to_csv(output_path, index=False)
                    print(f"✅ Market Day Saved (Includes Working Sat/Sun): {file_date}")

        except Exception as e:
            pass

        # NSE Server IP Safe Delay
        time.sleep(0.8)

if __name__ == "__main__":
    fetch_all_days_data(5000)
