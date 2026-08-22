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

            if 'PREV_CLOSE' in df.columns:
                df['PREV_CLOSE'] = pd.to_numeric(df['PREV_CLOSE'], errors='coerce')
                df['PRICE_CHG_PCT'] = ((df['CLOSE_PRICE'] - df['PREV_CLOSE']) / df['PREV_CLOSE']) * 100
            else:
                prev_close = df['CLOSE_PRICE'].shift(1)
                df['PRICE_CHG_PCT'] = ((df['CLOSE_PRICE'] - prev_close) / prev_close) * 100

            df['PRICE_CHG_PCT'] = df['PRICE_CHG_PCT'].fillna(0.0)

            if len(df) >= 11:
                symbol = os.path.basename(file).replace(".csv", "")
                all_stocks_data[symbol] = df
                available_dates.update(df['Date'].tolist()[10:])
                all_symbols_set.add(symbol)
        except Exception:
            pass

    sorted_dates = sorted(list(available_dates), reverse=True)
    sorted_symbols = sorted(list(all_symbols_set))
    
    target_dates = sorted_dates[:15]
    date_wise_results = {}
    
    for d in target_dates:
        day_stocks = []

        for symbol, df in all_stocks_data.items():
            if d in df['Date'].values:
                idx = df[df['Date'] == d].index[0]
                pos = df.index.get_loc(idx)
                if pos >= 10:
                    latest_row = df.iloc[pos]
                    chg_pct = float(latest_row['PRICE_CHG_PCT'])
                    day_stocks.append({'symbol': symbol, 'chg_pct': chg_pct, 'pos': pos, 'df': df, 'row': latest_row})

        day_stocks_sorted = sorted(day_stocks, key=lambda x: x['chg_pct'], reverse=True)
        
        top_gainers_map = {}
        for rank, s in enumerate(day_stocks_sorted[:5], 1):
            if s['chg_pct'] > 0:
                top_gainers_map[s['symbol']] = rank

        top_losers_map = {}
        for rank, s in enumerate(reversed(day_stocks_sorted[-5:]), 1):
            if s['chg_pct'] < 0:
                top_losers_map[s['symbol']] = rank

        results = []
        for item in day_stocks:
            symbol = item['symbol']
            pos = item['pos']
            df = item['df']
            latest_row = item['row']
            today_deliv = float(latest_row['DELIV_QTY'])
            chg_pct = item['chg_pct']

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

            tag = top_gainers_map.get(symbol, -top_losers_map.get(symbol, 0))

            results.append([
                str(d),                         # 0: Date
                str(symbol),                    # 1: Symbol
                round(float(max_spike), 2),     # 2: Max Spike
                round(float(latest_row['CLOSE_PRICE']), 2), # 3: Close
                int(latest_row['TTL_TRD_QNTY']),# 4: Traded Qty
                round(float(latest_row['TURNOVER_LACS']), 2), # 5: Turnover
                int(today_deliv),               # 6: Delivery Qty
                round(float(latest_row['DELIV_PER']), 2), # 7: Delivery %
                round(float(r2), 2),            # 8: R2
                round(float(r5), 2),            # 9: R5
                round(float(r7), 2),            # 10: R7
                round(float(r10), 2),           # 11: R10
                int(avg_2d),                    # 12: Avg 2D
                int(avg_5d),                    # 13: Avg 5D
                int(avg_7d),                    # 14: Avg 7D
                int(avg_10d),                   # 15: Avg 10D
                1 if is_2x_val else 0,          # 16: Is2x
                round(chg_pct, 2),              # 17: Price Change %
                tag                             # 18: Rank Tag
            ])
        date_wise_results[d] = sorted(results, key=lambda x: x[2], reverse=True)

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
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        th, td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
        th {{ background: #10b981; color: white; cursor: pointer; font-size: 11px; position: sticky; top: 0; z-index: 10; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        tr.clickable-row {{ cursor: pointer; }}
        tr.clickable-row:hover {{ background: #e2e8f0; }}
        .badge-green {{ background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .num {{ text-align: right; }}
        .filter-group {{ display: flex; gap: 4px; align-items: center; background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-size: 11px; }}

        /* Clean Mini Rank Badges */
        .tbl-gainer {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: bold; display: inline-block; }}
        .tbl-loser {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: bold; display: inline-block; }}

        /* Modal Badges */
        .tag-gainer {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 4px; display: inline-block; }}
        .tag-loser {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 4px; display: inline-block; }}
        .tag-normal {{ background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 4px; display: inline-block; }}

        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; padding: 12px; box-sizing: border-box; }}
        .modal-box {{ background: #fff; width: 100%; max-width: 420px; border-radius: 12px; padding: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); position: relative; animation: popIn 0.2s ease-out; }}
        @keyframes popIn {{ from {{ transform: scale(0.9); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; margin-bottom: 12px; }}
        .modal-title {{ font-size: 16px; font-weight: bold; color: #0f172a; }}
        .close-btn {{ background: #f1f5f9; border: none; font-size: 16px; font-weight: bold; border-radius: 50%; width: 28px; height: 28px; cursor: pointer; color: #64748b; }}
        .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; }}
        .detail-item {{ background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; }}
        .detail-label {{ color: #64748b; font-size: 10px; text-transform: uppercase; margin-bottom: 2px; }}
        .detail-value {{ font-size: 13px; font-weight: bold; color: #1e293b; }}
        .highlight {{ color: #10b981; }}
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
                        <th>Rank</th>
                        <th class="num" onclick="sortTable(3, true)">Max Spike ↕</th>
                        <th class="num" onclick="sortTable(4, true)">Close (₹) ↕</th>
                    </tr>
                </thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>

    <!-- Details Modal -->
    <div id="detailsModal" class="modal-overlay" onclick="closeModal(event)">
        <div class="modal-box" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div>
                    <span id="mSymbol" class="modal-title">SYMBOL</span>
                    <div id="mDateTag" style="margin-top: 4px;"></div>
                </div>
                <button class="close-btn" onclick="hideModal()">✕</button>
            </div>
            <div class="detail-grid">
                <div class="detail-item"><div class="detail-label">Close Price</div><div id="mClose" class="detail-value">₹0.00</div></div>
                <div class="detail-item"><div class="detail-label">Max Spike</div><div id="mSpike" class="detail-value highlight">0x</div></div>
                <div class="detail-item"><div class="detail-label">Delivery Qty</div><div id="mDelivQty" class="detail-value">0</div></div>
                <div class="detail-item"><div class="detail-label">Delivery %</div><div id="mDelivPer" class="detail-value">0%</div></div>
                <div class="detail-item"><div class="detail-label">Traded Qty</div><div id="mTradedQty" class="detail-value">0</div></div>
                <div class="detail-item"><div class="detail-label">Turnover (Lacs)</div><div id="mTurnover" class="detail-value">₹0</div></div>
                <div class="detail-item"><div class="detail-label">2D Ratio (Avg)</div><div id="mR2" class="detail-value">0x (0)</div></div>
                <div class="detail-item"><div class="detail-label">5D Ratio (Avg)</div><div id="mR5" class="detail-value">0x (0)</div></div>
                <div class="detail-item"><div class="detail-label">7D Ratio (Avg)</div><div id="mR7" class="detail-value">0x (0)</div></div>
                <div class="detail-item"><div class="detail-label">10D Ratio (Avg)</div><div id="mR10" class="detail-value">0x (0)</div></div>
            </div>
        </div>
    </div>

    <script>
        const storeData = {json_data};
        let currentRowsData = [];

        function getSuffix(num) {{
            if (num === 1) return '1st';
            if (num === 2) return '2nd';
            if (num === 3) return '3rd';
            return num + 'th';
        }}

        function renderData() {{
            const selectedSymbol = document.getElementById("singleSymbolSelect").value;
            const mode = document.getElementById("modeSelect").value;
            const startDate = document.getElementById("startDate").value;
            const endDate = document.getElementById("endDate").value;
            const tbody = document.getElementById("tableBody");
            
            let htmlBuffer = "";
            currentRowsData = [];

            Object.keys(storeData).forEach(date => {{
                if (date >= startDate && date <= endDate) {{
                    storeData[date].forEach(r => {{
                        let matchSymbol = (selectedSymbol === "ALL" || r[1] === selectedSymbol);
                        let matchMode = (selectedSymbol !== "ALL") ? true : (mode === "all" || r[16] === 1);

                        if (matchSymbol && matchMode) {{
                            currentRowsData.push(r);
                        }}
                    }});
                }}
            }});

            if (selectedSymbol !== "ALL") {{
                currentRowsData.sort((a, b) => b[0].localeCompare(a[0]));
            }} else {{
                currentRowsData.sort((a, b) => b[2] - a[2]);
            }}

            if (currentRowsData.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">कोई डेटा नहीं मिला।</td></tr>';
                return;
            }}

            currentRowsData.slice(0, 200).forEach((r, idx) => {{
                let rankTag = r[18];
                let tagHtml = '-';
                
                if (rankTag > 0) {{
                    tagHtml = `<span class="tbl-gainer">${{getSuffix(rankTag)}}</span>`;
                }} else if (rankTag < 0) {{
                    tagHtml = `<span class="tbl-loser">${{getSuffix(Math.abs(rankTag))}}</span>`;
                }}

                htmlBuffer += `<tr class="clickable-row" onclick="showModal(${{idx}})">
                    <td><b>${{r[0]}}</b></td>
                    <td><b>${{r[1]}}</b></td>
                    <td>${{tagHtml}}</td>
                    <td class="num"><span class="badge-green">${{r[2]}}x</span></td>
                    <td class="num">${{r[3].toFixed(2)}}</td>
                </tr>`;
            }});

            tbody.innerHTML = htmlBuffer;
            filterTable();
        }}

        function showModal(index) {{
            const r = currentRowsData[index];
            if (!r) return;

            document.getElementById("mSymbol").innerText = r[1];
            
            let tagHtml = `<span style="font-size: 11px; color: #64748b;">${{r[0]}}</span>`;
            let pctVal = r[17] > 0 ? `+${{r[17]}}%` : `${{r[17]}}%`;
            let rankTag = r[18];
            
            if (rankTag > 0) {{
                tagHtml += ` <span class="tag-gainer">🟢 Top ${{rankTag}} Gainer (${{pctVal}})</span>`;
            }} else if (rankTag < 0) {{
                tagHtml += ` <span class="tag-loser">🔴 Top ${{Math.abs(rankTag)}} Loser (${{pctVal}})</span>`;
            }} else {{
                let colorClass = r[17] >= 0 ? 'color: #16a34a;' : 'color: #dc2626;';
                tagHtml += ` <span class="tag-normal" style="${{colorClass}}">Change: ${{pctVal}}</span>`;
            }}

            document.getElementById("mDateTag").innerHTML = tagHtml;
            document.getElementById("mClose").innerText = `₹${{r[3].toFixed(2)}}`;
            document.getElementById("mSpike").innerText = `${{r[2]}}x`;
            document.getElementById("mDelivQty").innerText = r[6].toLocaleString();
            document.getElementById("mDelivPer").innerText = `${{r[7].toFixed(2)}}%`;
            document.getElementById("mTradedQty").innerText = r[4].toLocaleString();
            document.getElementById("mTurnover").innerText = `₹${{r[5].toLocaleString()}}`;
            
            document.getElementById("mR2").innerText = `${{r[8]}}x (${{r[12].toLocaleString()}})`;
            document.getElementById("mR5").innerText = `${{r[9]}}x (${{r[13].toLocaleString()}})`;
            document.getElementById("mR7").innerText = `${{r[10]}}x (${{r[14].toLocaleString()}})`;
            document.getElementById("mR10").innerText = `${{r[11]}}x (${{r[15].toLocaleString()}})`;

            document.getElementById("detailsModal").style.display = "flex";
        }}

        function hideModal() {{
            document.getElementById("detailsModal").style.display = "none";
        }}

        function closeModal(event) {{
            if (event.target.id === "detailsModal") {{
                hideModal();
            }}
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

    print("✅ `index.html` टेबल में सिर्फ Rank (1st, 2nd...) और Color Badges के साथ अपडेट हो गया!")

if __name__ == "__main__":
    generate_delivery_screener()
