import requests
import datetime
import os
import pandas as pd
import io
import time
import zoneinfo

def fetch_data_from_2010():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    os.makedirs("data", exist_ok=True)
    ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(ist_tz)
    
    # 2010-01-01 से लेकर आज तक के कुल दिन कैलकुलेट करना
    start_date = datetime.datetime(2010, 1, 1, tzinfo=ist_tz)
    total_days = (now_ist - start_date).days

    print(f"🚀 2010 से अब तक (कुल {total_days} दिन) का डेटा चेक/डाउनलोड किया जा रहा है...")

    success_count = 0

    for days_back in range(0, total_days):
        target_date = now_ist - datetime.timedelta(days=days_back)
        
        file_date = target_date.strftime("%Y-%m-%d") # उदा: 2010-01-04
        date_str = target_date.strftime("%d%m%Y")
        output_path = f"data/{file_date}.csv"

        # 1. जो फ़ाइलें पहले से data/ फ़ोल्डर में हैं, उन्हें तुरंत SKIP कर देगा
        if os.path.exists(output_path):
            continue

        url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"

        try:
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code == 200 and len(response.content) > 2000:
                df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
                df.columns = df.columns.str.strip()

                # 2. Holiday & Weekend Check via DATE1
                if 'DATE1' in df.columns:
                    actual_csv_date = pd.to_datetime(df['DATE1'].iloc[0]).strftime("%Y-%m-%d")
                    if actual_csv_date != file_date:
                        continue

                # 3. Filter Equity Segment
                if 'SERIES' in df.columns:
                    df = df[df['SERIES'].str.strip() == 'EQ']

                if len(df) > 100:
                    df.to_csv(output_path, index=False)
                    success_count += 1
                    print(f"✅ Saved Old Data ({success_count}): {file_date}")

        except Exception as e:
            pass

        time.sleep(0.4)

    print(f"\n🎉 2010 तक का बैकफ़िल पूरा हुआ! कुल नई फ़ाइलें सेव हुईं: {success_count}")

if __name__ == "__main__":
    fetch_data_from_2010()
