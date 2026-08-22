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
    all_symbols_set = set()

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
                all_symbols_set.add(symbol)
        except Exception:
            pass

    sorted_dates = sorted(list(available_dates), reverse=True)
    sorted_symbols = sorted(list(all_symbols_set))
    
    # 15 दिनों तक का डेटा ही रखेंगे ताकि साइज लाइट रहे
    target_dates = sorted_dates[:15]
    date_wise_results = {}
    
    for d in target_dates:
        results = []
        for symbol, df in all_stocks_data.items():
            if d in df['Date'].values:
                idx = df[df['Date'] == d].index[0]
                pos = df.index.get_loc(idx)
                
                if pos >= 10:
                    latest_row = df.iloc[pos]
                    today_deliv = float(latest_row['DELIV_QTY'])
                    
                    prev_df = df.iloc[pos-10:pos]
                    avg_2d = float(prev_df.iloc[-2:]['DELIV_QTY'].mean())
                    avg_5d = float(prev_df.iloc[-5:]['DELIV_QTY'].mean())
                    avg_7d = float(prev_df.iloc[-7:]['DELIV_QTY'].mean())
                    avg_10d = float(prev_df['DELIV_QTY'].mean())

                    r2 = (today_deliv / avg_2d) if avg_2d > 0 else 0.0
                    r5 = (today_deliv / avg_5d) if avg_5d > 0 else 0.0
                    r7 = (today_deliv / avg_7d) if avg_7d > 0 else 0.0
                    r10 = (today_deliv / avg_10d) if avg_10d > 0 else 0.0

                    max_spike = max(r2, r5, r7, r10)
                    is_2x_val = bool(r2 >= 2.0 or r5 >= 2.0 or r7 >= 2.0 or r10 >= 2.0)

                    # लाइटवेट डेटा की कुंजी
                    results.append([
                        str(d),                         # 0: Date
                        str(symbol),                    # 1: Symbol
                        round(float(latest_row['CLOSE_PRICE']), 2), # 2: Close
                        int(latest_row['TTL_TRD_QNTY']),# 3: Traded Qty
                        round(float(latest_row['TURNOVER_LACS']), 2), # 4: Turnover
                        int(today_deliv),               # 5: Deliv Qty
                        round(float(latest_row['DELIV_PER']), 2), # 6: Deliv %
                        round(float(r2), 2),            # 7: R2
                        round(float(r5), 2),            # 8: R5
                        round(float(r7), 2),            # 9: R7
                        round(float(r10), 2),           # 10: R10
                        round(float(max_spike), 2),      # 11: Max Spike
                        1 if is_2x_val else 0           # 12: Is2x
                    ])
        date_wise_results[d] = sorted(results, key=lambda x: x[11], reverse=True)

    json_data = json.dumps(date_wise_results, separators=(',', ':'))
    min_date = target_dates[-1] if target_dates else ""
    max_date = target_dates[0] if target_dates else ""

    symbol_options = '<option value="ALL">-- ALL SYMBOLS --</option>' + "".join([f'<option value="{s}">{s}</option>' for s in sorted_symbols])

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F&O Stock Screener</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f8f9fa; margin: 0; padding: 10px; color: #212529; }}
        .container {{ background: #fff; padding: 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        h2 {{ color: #1e293b; font-size: 18px; margin: 0 0 10px 0; }}
        .controls {{ display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }}
        .search-box, .select-box, .date-input {{ padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 12px; outline: none; }}
        .search-box {{ flex: 1; min-width: 130px; }}
        .table-responsive {{ width: 100%; overflow-x: auto; max-height: 70vh; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; min-width: 1000px; }}
        th, td {{ padding: 6px 8px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
        th {{ background: #10b981; color: white; cursor: pointer; font-size: 11px; position: sticky; top: 0; z-index: 10; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        .badge {{ background: #ef4444; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 10px; }}
        .badge-green {{ background: #10b981; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold; font-size: 10px; }}
        .num {{ text-align: right; }}
        .filter-group {{ display: flex; gap: 4px; align-items: center; background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 F&O Fast Stock Screener</h2>
        
        <div class="controls">
            <div class="filter-group">
                <label>Symbol:</label>
                <select id="singleSymbolSelect" class="select-box" onchange="renderData()">
                    {symbol_options}
                </select>
            </div>

            <div class="filter-group">
                <label>फ़िल्टर:</label>
                <select id="modeSelect" class="select-box" onchange="renderData()">
                    <option value="2x">Spike >= 2x Only</option>
                    <option value="all">All Stocks (No Filter)</option>
                </select>
            </div>

            <div class="filter-group">
                <label>Date:</label>
                <input type="date" id="startDate" class="date-input" value="{max_date}" min="{min_date}" max="{max_date}" onchange="renderData()">
                <span>से</span>
                <input type="date" id="endDate" class="date-input" value="{max_date}" min="{min_date}" max="{max_date}" onchange="renderData()">
            </div>

            <input type="text" id="searchInput" class="search-box" onkeyup="filterTable()" placeholder="🔍 Quick Search...">
        </div>

        <div class="table-responsive">
            <table id="screenerTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Date ↕</th>
                        <th onclick="sortTable(1)">Symbol ↕</th>
                        <th class="num" onclick="sortTable(11, true)">Max Spike ↕</th>
                        <th class="num" onclick="sortTable(2, true)">Close ↕</th>
                        <th class="num" onclick="sortTable(3, true)">Traded Qty ↕</th>
                        <th class="num" onclick="sortTable(4, true)">Turnover(L) ↕</th>
                        <th class="num" onclick="sortTable(5, true)">Deliv Qty ↕</th>
                        <th class="num" onclick="sortTable(6, true)">Deliv % ↕</th>
                        <th class="num" onclick="sortTable(7, true)">2D Ratio ↕</th>
                        <th class="num" onclick="sortTable(8, true)">5D Ratio ↕</th>
                        <th class="num" onclick="sortTable(9, true)">7D Ratio ↕</th>
                        <th class="num" onclick="sortTable(10, true)">10D Ratio ↕</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        const storeData = {json_data};

        function renderData() {{
            const selectedSymbol = document.getElementById("singleSymbolSelect").value;
            const mode = document.getElementById("modeSelect").value;
            const startDate = document.getElementById("startDate").value;
            const endDate = document.getElementById("endDate").value;
            const tbody = document.getElementById("tableBody");
            
            let htmlBuffer = "";
            let combinedRows = [];

            Object.keys(storeData).forEach(date => {{
                if (date >= startDate && date <= endDate) {{
                    storeData[date].forEach(r => {{
                        let matchSymbol = (selectedSymbol === "ALL" || r[1] === selectedSymbol);
                        let matchMode = (selectedSymbol !== "ALL") ? true : (mode === "all" || r[12] === 1);

                        if (matchSymbol && matchMode) {{
                            combinedRows.push(r);
                        }}
                    }});
                }}
            }});

            if (selectedSymbol !== "ALL") {{
                combinedRows.sort((a, b) => b[0].localeCompare(a[0]));
            }} else {{
                combinedRows.sort((a, b) => b[11] - a[11]);
            }}

            if (combinedRows.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="12" style="text-align:center; color:#94a3b8;">कोई डेटा नहीं मिला।</td></tr>';
                return;
            }}

            // केवल पहले 200 रिकॉर्ड्स रेंडर करें ताकि ब्राउज़र हैंग न हो
            combinedRows.slice(0, 200).forEach(r => {{
                let r2_badge = r[7] >= 2.0 ? `<span class="badge">${{r[7]}}x</span>` : `${{r[7]}}x`;
                let r5_badge = r[8] >= 2.0 ? `<span class="badge">${{r[8]}}x</span>` : `${{r[8]}}x`;
                let r7_badge = r[9] >= 2.0 ? `<span class="badge">${{r[9]}}x</span>` : `${{r[9]}}x`;
                let r10_badge = r[10] >= 2.0 ? `<span class="badge">${{r[10]}}x</span>` : `${{r[10]}}x`;

                htmlBuffer += `<tr>
                    <td><b>${{r[0]}}</b></td>
                    <td><b>${{r[1]}}</b></td>
                    <td class="num">${{r[2].toFixed(2)}}</td>
                    <td class="num">${{r[3].toLocaleString()}}</td>
                    <td class="num">${{r[4].toLocaleString()}}</td>
                    <td class="num">${{r[5].toLocaleString()}}</td>
                    <td class="num"><b>${{r[6].toFixed(2)}}%</b></td>
                    <td class="num">${{r2_badge}}</td>
                    <td class="num">${{r5_badge}}</td>
                    <td class="num">${{r7_badge}}</td>
                    <td class="num">${{r10_badge}}</td>
                    <td class="num"><span class="badge-green">${{r[11]}}x</span></td>
                </tr>`;
            }});

            tbody.innerHTML = htmlBuffer;
            filterTable();
        }}

        function filterTable() {{
            let input = document.getElementById("searchInput").value.toUpperCase();
            let tr = document.getElementById("tableBody").getElementsByTagName("tr");
            for (let i = 0; i < tr.length; i++) {{
                let tdSymbol = tr[i].getElementsByTagName("td")[1];
                if (tdSymbol) {{
                    tr[i].style.display = (tdSymbol.textContent || tdSymbol.innerText).toUpperCase().indexOf(input) > -1 ? "" : "none";
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

    print("✅ `index.html` सुपर-फास्ट और नो-हैंड कोड के साथ अपडेट हो गया!")

if __name__ == "__main__":
    generate_delivery_screener()
