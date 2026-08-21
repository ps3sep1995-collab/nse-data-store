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

            for col in ['DELIV_QTY', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values(by='Date', ascending=True)

            if len(df) < 11:
                continue

            latest_row = df.iloc[-1]
            latest_date_str = latest_row['Date'].strftime('%Y-%m-%d')
            today_deliv = latest_row['DELIV_QTY']

            if today_deliv == 0:
                continue

            prev_df = df.iloc[:-1]
            avg_5d = prev_df.iloc[-5:]['DELIV_QTY'].mean()
            avg_7d = prev_df.iloc[-7:]['DELIV_QTY'].mean()
            avg_10d = prev_df.iloc[-10:]['DELIV_QTY'].mean()

            if avg_5d > 0 and avg_7d > 0 and avg_10d > 0:
                ratio_5d = today_deliv / avg_5d
                ratio_7d = today_deliv / avg_7d
                ratio_10d = today_deliv / avg_10d

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

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Stock Delivery Screener</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8f9fa; margin: 0; padding: 12px; color: #212529; }}
        .container {{ max-width: 100%; margin: 0 auto; background: #fff; padding: 18px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ color: #1e293b; font-size: 22px; margin: 0 0 6px 0; }}
        p.subtitle {{ color: #64748b; font-size: 13px; margin-bottom: 18px; }}
        
        .controls {{ display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; align-items: center; }}
        .search-box {{ flex: 1; min-width: 200px; padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; outline: none; }}
        .search-box:focus {{ border-color: #10b981; box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2); }}
        .stats-badge {{ background-color: #f1f5f9; color: #475569; padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; }}

        .table-responsive {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 900px; }}
        th, td {{ padding: 11px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
        th {{ background-color: #10b981; color: white; font-weight: 600; text-transform: uppercase; font-size: 11px; cursor: pointer; user-select: none; position: sticky; top: 0; }}
        th:hover {{ background-color: #059669; }}
        tr:nth-child(even) {{ background-color: #f8fafc; }}
        tr:hover {{ background-color: #f1f5f9; }}
        .badge {{ background-color: #ef4444; color: white; padding: 4px 7px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .num {{ text-align: right; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 F&O Delivery & Turnover Screener</h2>
        <p class="subtitle">तारीख: <b>{latest_date_str}</b> | फ़िल्टर: 5D, 7D, 10D Avg से Delivery Qty <b>≥ 2x</b></p>
        
        <div class="controls">
            <input type="text" id="searchInput" class="search-box" onkeyup="filterTable()" placeholder="🔍 Symbol खोजें (e.g. RELIANCE, SBIN)...">
            <div class="stats-badge">कुल स्टॉक्स: <span id="stockCount">{len(results_df)}</span></div>
        </div>

        <div class="table-responsive">
            <table id="screenerTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Symbol ↕</th>
                        <th class="num" onclick="sortTable(1, true)">Close (₹) ↕</th>
                        <th class="num" onclick="sortTable(2, true)">Traded Qty ↕</th>
                        <th class="num" onclick="sortTable(3, true)">Turnover (Lakh) ↕</th>
                        <th class="num" onclick="sortTable(4, true)">Today Deliv ↕</th>
                        <th class="num" onclick="sortTable(5, true)">Deliv % ↕</th>
                        <th class="num" onclick="sortTable(6, true)">5D Avg ↕</th>
                        <th class="num" onclick="sortTable(7, true)">7D Avg ↕</th>
                        <th class="num" onclick="sortTable(8, true)">10D Avg ↕</th>
                        <th class="num" onclick="sortTable(9, true)">Spike ↕</th>
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
                        <td colspan="10" style="text-align: center; color: #94a3b8;">आज कोई फ़िल्टर मैच नहीं हुआ।</td>
                    </tr>
"""

    html_content += """
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function filterTable() {
            let input = document.getElementById("searchInput").value.toUpperCase();
            let table = document.getElementById("screenerTable");
            let tr = table.getElementsByTagName("tr");
            let count = 0;

            for (let i = 1; i < tr.length; i++) {
                let td = tr[i].getElementsByTagName("td")[0];
                if (td) {
                    let txtValue = td.textContent || td.innerText;
                    if (txtValue.toUpperCase().indexOf(input) > -1) {
                        tr[i].style.display = "";
                        count++;
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
            document.getElementById("stockCount").innerText = count;
        }

        function sortTable(n, isNumeric = false) {
            let table = document.getElementById("screenerTable");
            let rows = Array.from(table.rows).slice(1);
            let dir = table.dataset.sortDir === "asc" ? "desc" : "asc";
            table.dataset.sortDir = dir;

            rows.sort((a, b) => {
                let x = a.cells[n].innerText.replace(/,/g, '').replace('%', '').replace('x', '').trim();
                let y = b.cells[n].innerText.replace(/,/g, '').replace('%', '').replace('x', '').trim();
                
                if (isNumeric) {
                    return dir === "asc" ? parseFloat(x) - parseFloat(y) : parseFloat(y) - parseFloat(x);
                } else {
                    return dir === "asc" ? x.localeCompare(y) : y.localeCompare(x);
                }
            });

            rows.forEach(row => table.querySelector("tbody").appendChild(row));
        }
    </script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ `index.html` Search Box और Sorting Features के साथ अपडेट हो गया!")

if __name__ == "__main__":
    generate_delivery_screener()
