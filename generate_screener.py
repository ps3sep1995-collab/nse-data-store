import os
import glob
import pandas as pd

def generate_delivery_screener():
    stocks_folder = "stocks"
    stock_files = glob.glob(os.path.join(stocks_folder, "*.csv"))

    if not stock_files:
        print("❌ `stocks/` फ़ोल्डर में कोई फ़ाइल नहीं मिली।")
        return

    results = []
    latest_date_str = ""

    for file in stock_files:
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()

            required_cols = ['DELIV_QTY', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']
            if not all(col in df.columns for col in required_cols):
                continue

            # numeric डेटा क्लीन-अप
            for col in ['DELIV_QTY', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values(by='Date', ascending=True)

            # कम से कम 11 दिनों का इतिहास आवश्यक (10D Avg + Today)
            if len(df) < 11:
                continue

            latest_row = df.iloc[-1]
            latest_date_str = latest_row['Date'].strftime('%Y-%m-%d')
            today_deliv = latest_row['DELIV_QTY']

            if today_deliv == 0:
                continue

            # पिछले 5, 7, और 10 दिनों का औसत
            prev_df = df.iloc[:-1]
            avg_5d = prev_df.iloc[-5:]['DELIV_QTY'].mean()
            avg_7d = prev_df.iloc[-7:]['DELIV_QTY'].mean()
            avg_10d = prev_df.iloc[-10:]['DELIV_QTY'].mean()

            if avg_5d > 0 and avg_7d > 0 and avg_10d > 0:
                ratio_5d = today_deliv / avg_5d
                ratio_7d = today_deliv / avg_7d
                ratio_10d = today_deliv / avg_10d

                # शर्त: 5D, 7D और 10D तीनों के औसत से 2x या अधिक
                if ratio_5d >= 2.0 and ratio_7d >= 2.0 and ratio_10d >= 2.0:
                    symbol = os.path.basename(file).replace(".csv", "")
                    results.append({
                        'Symbol': symbol,
                        'Close_Price': latest_row['CLOSE_PRICE'],
                        'Traded_Qty': int(latest_row['TTL_TRD_QNTY']),
                        'Turnover_Lacs': latest_row['TURNOVER_LACS'],
                        'Today_Deliv': int(today_deliv),
                        'Deliv_Per': latest_row['DELIV_PER'],
                        'Avg_5D': int(avg_5d),
                        'Avg_7D': int(avg_7d),
                        'Avg_10D': int(avg_10d),
                        'Multiple_10D': round(ratio_10d, 2)
                    })
        except Exception as e:
            pass

    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(by='Multiple_10D', ascending=False)

    # Responsive HTML Dashboard
    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Stock Delivery Screener</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 15px; color: #333; }}
        .container {{ max-width: 1250px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow-x: auto; }}
        h2 {{ color: #2c3e50; margin-bottom: 5px; }}
        p.subtitle {{ color: #7f8c8d; font-size: 14px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #ddd; white-space: nowrap; }}
        th {{ background-color: #27ae60; color: white; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
        tr:hover {{ background-color: #f1f8f5; }}
        .badge {{ background-color: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        .num {{ text-align: right; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 F&O Complete Delivery & Turnover Screener</h2>
        <p class="subtitle">तारीख: <b>{latest_date_str}</b> | फिल्टर: 5D, 7D और 10D Average से Delivery Qty <b>≥ 2x</b> है।</p>
        
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th class="num">Close (₹)</th>
                    <th class="num">Traded Qty</th>
                    <th class="num">Turnover (Lakhs)</th>
                    <th class="num">Today Delivery</th>
                    <th class="num">Delivery %</th>
                    <th class="num">5D Avg</th>
                    <th class="num">7D Avg</th>
                    <th class="num">10D Avg</th>
                    <th class="num">Spike</th>
                </tr>
            </thead>
            <tbody>
"""

    if not results_df.empty:
        for _, row in results_df.iterrows():
            html_content += f"""
                <tr>
                    <td><b>{row['Symbol']}</b></td>
                    <td class="num">{row['Close_Price']:.2f}</td>
                    <td class="num">{row['Traded_Qty']:,}</td>
                    <td class="num">{row['Turnover_Lacs']:,.2f}</td>
                    <td class="num">{row['Today_Deliv']:,}</td>
                    <td class="num"><b>{row['Deliv_Per']:.2f}%</b></td>
                    <td class="num">{row['Avg_5D']:,}</td>
                    <td class="num">{row['Avg_7D']:,}</td>
                    <td class="num">{row['Avg_10D']:,}</td>
                    <td class="num"><span class="badge">{row['Multiple_10D']}x</span></td>
                </tr>
"""
    else:
        html_content += """
                <tr>
                    <td colspan="10" style="text-align: center; color: #7f8c8d;">आज कोई भी F&O स्टॉक इस 2x Delivery Spike फ़िल्टर को पूरा नहीं करता है।</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ `index.html` पूर्ण डेटा (Traded Qty, Turnover, Deliv %) के साथ अपडेट हो गया!")

if __name__ == "__main__":
    generate_delivery_screener()
