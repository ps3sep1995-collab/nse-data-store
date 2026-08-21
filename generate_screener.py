import os
import glob
import pandas as pd
import json

def generate_delivery_screener():
    stocks_folder = "stocks"
    stock_files = glob.glob(os.path.join(stocks_folder, "*.csv"))

    if not stock_files:
        print("❌ `stocks/` फ़ोल्डर में कोई फ़ाइल नहीं मिली।")
        return

    all_stocks_data = {}
    available_dates = set()

    for file in stock_files:
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()

            required_cols = ['DELIV_QTY', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']
            if not all(col in df.columns for col in required_cols):
                continue

            for col in ['DELIV_QTY', 'CLOSE_PRICE', 'TTL_TRD_QNTY', 'TURNOVER_LACS', 'DELIV_PER']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
            df = df.sort_values(by='Date', ascending=True)

            if len(df) >= 11:
                symbol = os.path.basename(file).replace(".csv", "")
                all_stocks_data[symbol] = df
                available_dates.update(df['Date'].tolist()[10:])
        except Exception:
            pass

    sorted_dates = sorted(list(available_dates), reverse=True)
    date_wise_results = {}
    
    for d in sorted_dates[:15]:
        results = []
        for symbol, df in all_stocks_data.items():
            if d in df['Date'].values:
                idx = df[df['Date'] == d].index[0]
                pos = df.index.get_loc(idx)
                
                if pos >= 10:
                    latest_row = df.iloc[pos]
                    today_deliv = latest_row['DELIV_QTY']
                    
                    if today_deliv > 0:
                        prev_df = df.iloc[pos-10:pos]
                        avg_5d = prev_df.iloc[-5:]['DELIV_QTY'].mean()
                        avg_7d = prev_df.iloc[-7:]['DELIV_QTY'].mean()
                        avg_10d = prev_df['DELIV_QTY'].mean()

                        if avg_5d > 0 and avg_7d > 0 and avg_10d > 0:
                            r5 = today_deliv / avg_5d
                            r7 = today_deliv / avg_7d
                            r10 = today_deliv / avg_10d

                            # बदला हुआ लॉजिक: 5D, 7D या 10D किसी भी एक में 2x या उससे ज्यादा हो (OR Condition)
                            if r5 >= 2.0 or r7 >= 2.0 or r10 >= 2.0:
                                max_spike = max(r5, r7, r10)
                                results.append({
                                    'Symbol': symbol,
                                    'Close_Price': round(latest_row['CLOSE_PRICE'], 2),
                                    'Traded_Qty': int(latest_row['TTL_TRD_QNTY']),
                                    'Turnover_Lacs': round(latest_row['TURNOVER_LACS'], 2),
                                    'Today_Deliv': int(today_deliv),
                                    'Deliv_Per': round(latest_row['DELIV_PER'], 2),
                                    'Avg_5D': int(avg_5d),
                                    'Avg_7D': int(avg_7d),
                                    'Avg_10D': int(avg_10d),
                                    'R_5D': round(r5, 2),
                                    'R_7D': round(r7, 2),
                                    'R_10D': round(r10, 2),
                                    'Max_Spike': round(max_spike, 2)
                                })
        date_wise_results[d] = sorted(results, key=lambda x: x['Max_Spike'], reverse=True)

    json_data = json.dumps(date_wise_results)
    date_options = "".join([f'<option value="{d}">{d}</option>' for d in sorted_dates[:15]])

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Stock Delivery Screener</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; margin: 0; padding: 12px; color: #212529; }}
        .container {{ max-width: 100%; background: #fff; padding: 16px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ color: #1e293b; font-size: 20px; margin: 0 0 6px 0; }}
        p.subtitle {{ color: #64748b; font-size: 13px; margin-bottom: 16px; }}
        .controls {{ display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }}
        .search-box, .date-select {{ padding: 9px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; outline: none; }}
        .search-box {{ flex: 1; min-width: 180px; }}
        .date-select {{ background: #fff; cursor: pointer; }}
        .table-responsive {{ width: 100%; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 1000px; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
        th {{ background: #10b981; color: white; cursor: pointer; font-size: 11px; text-transform: uppercase; position: sticky; top: 0; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .badge {{ background: #ef4444; color: white; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .badge-green {{ background: #10b981; color: white; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .num {{ text-align: right; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 F&O Delivery & Turnover Screener</h2>
        <p class="subtitle">फ़िल्टर: 5D, 7D या 10D Avg में से किसी में भी Delivery Qty <b>≥ 2x</b></p>
        
        <div class="controls">
            <select id="dateSelect" class="date-select" onchange="renderData()">
                {date_options}
            </select>
            <input type="text" id="searchInput" class="search-box" onkeyup="filterTable()" placeholder="🔍 Symbol खोजें (e.g. SBIN, ITC)...">
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
                        <th class="num" onclick="sortTable(6, true)">5D Ratio ↕</th>
                        <th class="num" onclick="sortTable(7, true)">7D Ratio ↕</th>
                        <th class="num" onclick="sortTable(8, true)">10D Ratio ↕</th>
                        <th class="num" onclick="sortTable(9, true)">Max Spike ↕</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        const storeData = {json_data};

        function renderData() {{
            const date = document.getElementById("dateSelect").value;
            const rows = storeData[date] || [];
            const tbody = document.getElementById("tableBody");
            tbody.innerHTML = "";

            if (rows.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; color:#94a3b8;">इस तारीख के लिए कोई स्टॉक फ़िल्टर मैच नहीं हुआ।</td></tr>';
                return;
            }}

            rows.forEach(r => {{
                let r5_badge = r.R_5D >= 2.0 ? `<span class="badge">${{r.R_5D}}x</span>` : `${{r.R_5D}}x`;
                let r7_badge = r.R_7D >= 2.0 ? `<span class="badge">${{r.R_7D}}x</span>` : `${{r.R_7D}}x`;
                let r10_badge = r.R_10D >= 2.0 ? `<span class="badge">${{r.R_10D}}x</span>` : `${{r.R_10D}}x`;

                tbody.innerHTML += `<tr>
                    <td><b>${{r.Symbol}}</b></td>
                    <td class="num">${{r.Close_Price.toFixed(2)}}</td>
                    <td class="num">${{r.Traded_Qty.toLocaleString()}}</td>
                    <td class="num">${{r.Turnover_Lacs.toLocaleString()}}</td>
                    <td class="num">${{r.Today_Deliv.toLocaleString()}}</td>
                    <td class="num"><b>${{r.Deliv_Per.toFixed(2)}}%</b></td>
                    <td class="num">${{r5_badge}}</td>
                    <td class="num">${{r7_badge}}</td>
                    <td class="num">${{r10_badge}}</td>
                    <td class="num"><span class="badge-green">${{r.Max_Spike}}x</span></td>
                </tr>`;
            }});
            filterTable();
        }}

        function filterTable() {{
            let input = document.getElementById("searchInput").value.toUpperCase();
            let tr = document.getElementById("tableBody").getElementsByTagName("tr");
            for (let i = 0; i < tr.length; i++) {{
                let td = tr[i].getElementsByTagName("td")[0];
                if (td) {{
                    tr[i].style.display = (td.textContent || td.innerText).toUpperCase().indexOf(input) > -1 ? "" : "none";
                }}
            }}
        }}

        function sortTable(n, isNumeric = false) {{
            let table = document.getElementById("screenerTable");
            let rows = Array.from(table.rows).slice(1);
            let dir = table.dataset.sortDir === "asc" ? "desc" : "asc";
            table.dataset.sortDir = dir;

            rows.sort((a, b) => {{
                let x = a.cells[n].innerText.replace(/,/g, '').replace('%', '').replace('x', '').trim();
                let y = b.cells[n].innerText.replace(/,/g, '').replace('%', '').replace('x', '').trim();
                return isNumeric ? (dir === "asc" ? x - y : y - x) : (dir === "asc" ? x.localeCompare(y) : y.localeCompare(x));
            }});
            rows.forEach(row => document.getElementById("tableBody").appendChild(row));
        }}

        renderData();
    </script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ `index.html` Flexible OR Logic के साथ अपडेट हो गया!")

if __name__ == "__main__":
    generate_delivery_screener()
