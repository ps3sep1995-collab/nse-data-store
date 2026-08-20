import requests
import datetime
import os
import pandas as pd
import io

def fetch_last_month():
    # पिछले 30 दिनों का डेटा फ़ेच करने के लिए
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    os.makedirs("data", exist_ok=True)
    success_count = 0

    print("🚀 Fetching last 30 days data...")

    for days_back in range(0, 30):
        target_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        date_str = target_date.strftime("%d%m%Y")
        file_date = target_date.strftime("%Y-%m-%d")
        
        output_path = f"data/{file_date}.csv"
        
        # अगर फ़ाइल पहले से है, तो दुबारा डाउनलोड न करें
        if os.path.exists(output_path):
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
                print(f"⏩ Skipped (Weekend/Holiday): {file_date}")
        except Exception as e:
            print(f"❌ Error for {file_date}: {e}")

    print(f"\n🎉 Finished! Total new files added: {success_count}")

if __name__ == "__main__":
    fetch_last_month()
