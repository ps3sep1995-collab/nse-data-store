import os
import glob
import pandas as pd
import json

def generate_delivery_screener():
    stocks_folder = "stocks"
    stock_files = glob.glob(os.path.join(stocks_folder, "*.csv"))

    if not stock_files:
        print("❌ `stocks/` फ़ोल्डर में कोई CSV फ़ाइल नहीं मिली।")
        return

    all_stocks_data = {}
    available_dates = set()
    all_symbols_set = set()
    all_sectors_set = set()
    all_indices_set = set()
    stock_full_history = {}

    print(f"📊 कुल {len(stock_files)} CSV फ़ाइलों से डेटा लोड किया जा रहा है...")

    for file in stock_files:
        try:
            df = pd.read_csv(file)
            symbol = os.path.basename(file).replace(".csv", "").upper()

            if len(df) < 1:
                continue

            # Get Metadata from Enriched CSV
            sector = str(df['SECTOR'].iloc[0]) if 'SECTOR' in df.columns else "Others"
            indices_str = str(df['INDICES'].iloc[0]) if 'INDICES' in df.columns else "F&O"

            all_stocks_data[symbol] = (df, sector, indices_str)
            available_dates.update(df['Date'].astype(str).tolist())
            all_symbols_set.add(symbol)
            all_sectors_set.add(sector)
            
            for idx in indices_str.split(", "):
                if idx.strip():
                    all_indices_set.add(idx.strip())

            # History for Modal (Directly reading CSV Columns)
            history_list = []
            for i in range(len(df)):
                history_list.append({
                    'date': str(df.iloc[i]['Date']),
                    'open': round(float(df.iloc[i].get('OPEN_PRICE', 0)), 2),
                    'high': round(float(df.iloc[i].get('HIGH_PRICE', 0)), 2),
                    'low': round(float(df.iloc[i].get('LOW_PRICE', 0)), 2),
                    'close': round(float(df.iloc[i].get('CLOSE_PRICE', 0)), 2),
                    'ttq': int(df.iloc[i].get('TTL_TRD_QNTY', 0)),
                    'deliv': int(df.iloc[i].get('DELIV_QTY', 0)),
                    'deliv_per': round(float(df.iloc[i].get('DELIV_PER', 0)), 2),
                    'spike': round(float(df.iloc[i].get('MAX_SPIKE', 0)), 2),
                    'chg_pct': round(float(df.iloc[i].get('PRICE_CHG_PCT', 0)), 2)
                })
            stock_full_history[symbol] = history_list

        except Exception as e:
            print(f"⚠️ Error reading {file}: {e}")

    sorted_dates = sorted(list(available_dates), reverse=True)
    sorted_symbols = sorted(list(all_symbols_set))
    sorted_sectors = sorted(list(all_sectors_set))
    sorted_indices = sorted(list(all_indices_set))

    target_dates = sorted_dates[:15]
    date_wise_results = {}

    for d in target_dates:
        day_stocks = []

        for symbol, (df, sector, indices_str) in all_stocks_data.items():
            if d in df['Date'].astype(str).values:
                latest_row = df[df['Date'].astype(str) == d].iloc[0]
                chg_pct = float(latest_row.get('PRICE_CHG_PCT', 0.0))
                day_stocks.append({
                    'symbol': symbol, 
                    'sector': sector, 
                    'indices': indices_str, 
                    'chg_pct': chg_pct, 
                    'row': latest_row
                })

        # Calculate Rank Tagging (Top Gainers / Losers)
        day_stocks_sorted = sorted(day_stocks, key=lambda x: x['chg_pct'], reverse=True)
        top_gainers_map = {s['symbol']: rank for rank, s in enumerate(day_stocks_sorted[:5], 1) if s['chg_pct'] > 0}
        top_losers_map = {s['symbol']: rank for rank, s in enumerate(reversed(day_stocks_sorted[-5:]), 1) if s['chg_pct'] < 0}

        results = []
        for item in day_stocks:
            symbol = item['symbol']
            sector = item['sector']
            indices_str = item['indices']
            latest_row = item['row']
            tag = top_gainers_map.get(symbol, -top_losers_map.get(symbol, 0))

            results.append([
                str(d),                                                     # 0: Date
                str(symbol),                                                # 1: Symbol
                round(float(latest_row.get('MAX_SPIKE', 0)), 2),            # 2: Max Spike
                round(float(latest_row.get('CLOSE_PRICE', 0)), 2),          # 3: Close
                int(latest_row.get('TTL_TRD_QNTY', 0)),                     # 4: Traded Qty
                round(float(latest_row.get('TURNOVER_LACS', 0)), 2),        # 5: Turnover
                int(latest_row.get('DELIV_QTY', 0)),                        # 6: Delivery Qty
                round(float(latest_row.get('DELIV_PER', 0)), 2),            # 7: Delivery %
                round(float(latest_row.get('R2', 0)), 2),                   # 8: R2
                round(float(latest_row.get('R5', 0)), 2),                   # 9: R5
                round(float(latest_row.get('R7', 0)), 2),                   # 10: R7
                round(float(latest_row.get('R10', 0)), 2),                  # 11: R10
                int(latest_row.get('AVG_DELIV_2D', 0)),                     # 12: Avg 2D
                int(latest_row.get('AVG_DELIV_5D', 0)),                     # 13: Avg 5D
                int(latest_row.get('AVG_DELIV_7D', 0)),                     # 14: Avg 7D
                int(latest_row.get('AVG_DELIV_10D', 0)),                    # 15: Avg 10D
                int(latest_row.get('IS_2X', 0)),                            # 16: Is2x
                round(float(latest_row.get('PRICE_CHG_PCT', 0)), 2),        # 17: Price Change %
                tag,                                                        # 18: Rank Tag
                str(sector),                                                # 19: Sector Name
                str(indices_str),                                           # 20: Indices String
                round(float(latest_row.get('OPEN_PRICE', 0)), 2),           # 21: Open
                round(float(latest_row.get('HIGH_PRICE', 0)), 2),           # 22: High
                round(float(latest_row.get('LOW_PRICE', 0)), 2)             # 23: Low
            ])
        date_wise_results[d] = sorted(results, key=lambda x: x[2], reverse=True)

    json_data = json.dumps(date_wise_results, separators=(',', ':'))
    json_history = json.dumps(stock_full_history, separators=(',', ':'))

    min_date = target_dates[-1] if target_dates else ""
    max_date = target_dates[0] if target_dates else ""

    symbol_options = '<option value="ALL">-- ALL SYMBOLS --</option>' + "".join([f'<option value="{s}">{s}</option>' for s in sorted_symbols])
    sector_options = '<option value="ALL">-- ALL SECTORS --</option>' + "".join([f'<option value="{sec}">{sec}</option>' for sec in sorted_sectors])
    index_options = '<option value="ALL">-- ALL INDICES --</option>' + "".join([f'<option value="{idx}">{idx}</option>' for idx in sorted_indices])

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Screener Dashboard</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #f8f9fa; margin: 0; padding: 12px; color: #1e293b; }}
        .container {{ background: #fff; padding: 16px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        h2 {{ margin: 0 0 12px 0; font-size: 20px; color: #0f172a; }}
        .controls {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; align-items: center; }}
        .select-box, .date-input, .search-box {{ padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; outline: none; }}
        .search-box {{ flex: 1; min-width: 140px; }}
        .table-responsive {{ width: 100%; overflow-x: auto; max-height: 72vh; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        th, td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
        th {{ background: #10b981; color: white; cursor: pointer; position: sticky; top: 0; z-index: 10; font-weight: 600; }}
        tr.clickable-row {{ cursor: pointer; }}
        tr.clickable-row:hover {{ background: #f1f5f9; }}
        .num {{ text-align: right; }}
        .badge-green {{ background: #10b981; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .badge-sector {{ background: #e2e8f0; color: #334155; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
        .badge-index {{ background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 2px; }}

        /* Slanted Rank Box */
        .rank-slanted-box {{ display: inline-flex; flex-direction: column; padding: 2px 8px; border-radius: 4px; font-weight: bold; line-height: 1.1; min-width: 46px; text-align: center; }}
        .fraction-gainer {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
        .fraction-loser {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}

        /* Modal Overlay */
        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; justify-content: center; align-items: center; padding: 12px; box-sizing: border-box; }}
        .modal-box {{ background: #fff; width: 100%; max-width: 540px; max-height: 90vh; overflow-y: auto; border-radius: 12px; padding: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; margin-bottom: 12px; }}
        .close-btn {{ background: #f1f5f9; border: none; border-radius: 50%; width: 28px; height: 28px; cursor: pointer; color: #64748b; font-weight: bold; }}
        .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; margin-top: 10px; }}
        .detail-item {{ background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0; }}
        .detail-label {{ color: #64748b; font-size: 10px; text-transform: uppercase; }}
        .detail-value {{ font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 2px; }}
        .history-table {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px; }}
        .history-table th {{ background: #f1f5f9; color: #475569; position: static; padding: 4px 6px; }}
        .history-table td {{ padding: 4px 6px; border-bottom: 1px solid #f1f5f9; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Stock Delivery & OHLC Screener</h2>
        
        <div class="controls">
            <select id="sortBySelect" class="select-box" onchange="renderData()">
                <option value="spike">Max Spike (Highest)</option>
                <option value="gainers">Top Rank % Gainers</option>
                <option value="losers">Top Rank % Losers</option>
            </select>

            <select id="singleSymbolSelect" class="select-box" onchange="renderData()">
                {symbol_options}
            </select>

            <select id="indexSelect" class="select-box" onchange="renderData()">
                {index_options}
            </select>

            <select id="sectorSelect" class="select-box" onchange="renderData()">
                {sector_options}
            </select>

            <select id="modeSelect" class="select-box" onchange="renderData()">
                <option value="2x">Spike >= 2x Only</option>
                <option value="all">All Stocks</option>
            </select>

            <input type="date" id="startDate" class="date-input" value="{max_date}" min="{min_date}" max="{max_date}" onchange="renderData()">
            <input type="date" id="endDate" class="date-input" value="{max_date}" min="{min_date}" max="{max_date}" onchange="renderData()">

            <input type="text" id="searchInput" class="search-box" onkeyup="filterTable()" placeholder="🔍 Quick Search...">
        </div>

        <div class="table-responsive">
            <table id="screenerTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Date ↕</th>
                        <th onclick="sortTable(1)">Symbol ↕</th>
                        <th onclick="sortTable(2, true)">Rank % Change ↕</th>
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
                    <span id="mSymbol" style="font-size:16px; font-weight:bold;">SYMBOL</span>
                    <span id="mSectorBadge" class="badge-sector">Sector</span>
                    <div id="mIndexBadges" style="margin-top: 4px;"></div>
                    <div id="mDateTag" style="margin-top: 4px;"></div>
                </div>
                <button class="close-btn" onclick="hideModal()">✕</button>
            </div>

            <!-- OHLC Section -->
            <div style="background: #f1f5f9; padding: 8px; border-radius: 6px; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; text-align: center; gap: 4px;">
                <div><div style="font-size: 10px; color: #64748b;">OPEN</div><div id="mOpen" style="font-size: 12px; font-weight: bold;">₹0</div></div>
                <div><div style="font-size: 10px; color: #16a34a;">HIGH</div><div id="mHigh" style="font-size: 12px; font-weight: bold; color: #16a34a;">₹0</div></div>
                <div><div style="font-size: 10px; color: #dc2626;">LOW</div><div id="mLow" style="font-size: 12px; font-weight: bold; color: #dc2626;">₹0</div></div>
                <div><div style="font-size: 10px; color: #0284c7;">CLOSE</div><div id="mClose" style="font-size: 12px; font-weight: bold; color: #0284c7;">₹0</div></div>
            </div>

            <div class="detail-grid">
                <div class="detail-item"><div class="detail-label">Max Spike</div><div id="mSpike" class="detail-value" style="color:#10b981;">0x</div></div>
                <div class="detail-item"><div class="detail-label">Delivery Qty</div><div id="mDelivQty" class="detail-value">0</div></div>
                <div class="detail-item"><div class="detail-label">Delivery %</div><div id="mDelivPer" class="detail-value">0%</div></div>
                <div class="detail-item"><div class="detail-label">Traded Qty</div><div id="mTradedQty" class="detail-value">0</div></div>
                <div class="detail-item"><div class="detail-label">Turnover (Lacs)</div><div id="mTurnover" class="detail-value">₹0</div></div>
                <div class="detail-item"><div class="detail-label">2D Ratio (Avg)</div><div id="mR2" class="detail-value">0x (0)</div></div>
                <div class="detail-item"><div class="detail-label">5D Ratio (Avg)</div><div id="mR5" class="detail-value">0x (0)</div></div>
                <div class="detail-item"><div class="detail-label">7D Ratio (Avg)</div><div id="mR7" class="detail-value">0x (0)</div></div>
                <div class="detail-item"><div class="detail-label">10D Ratio (Avg)</div><div id="mR10" class="detail-value">0x (0)</div></div>
            </div>

            <hr style="border: 0; height: 1px; background: #cbd5e1; margin: 16px 0 12px 0;">
            <div style="font-size: 13px; font-weight: bold; color: #334155;">📅 Recent OHLC & Delivery History:</div>
            <div style="overflow-x: auto;">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th class="num">O / H / L / C</th>
                            <th class="num">Deliv Qty</th>
                            <th class="num">Change %</th>
                            <th class="num">Spike</th>
                        </tr>
                    </thead>
                    <tbody id="mHistoryBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const storeData = {json_data};
        const stockHistory = {json_history};
        let currentRowsData = [];

        function getSuffix(num) {{
            if (num === 1) return '1st';
            if (num === 2) return '2nd';
            if (num === 3) return '3rd';
            return num + 'th';
        }}

        function renderData() {{
            const sortBy = document.getElementById("sortBySelect").value;
            const selectedSymbol = document.getElementById("singleSymbolSelect").value;
            const selectedSector = document.getElementById("sectorSelect").value;
            const selectedIndex = document.getElementById("indexSelect").value;
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
                        let matchSector = (selectedSector === "ALL" || r[19] === selectedSector);
                        let matchIndex = (selectedIndex === "ALL" || r[20].includes(selectedIndex));
                        let matchMode = (selectedSymbol !== "ALL") ? true : (mode === "all" || r[16] === 1);

                        if (matchSymbol && matchSector && matchIndex && matchMode) {{
                            currentRowsData.push(r);
                        }}
                    }});
                }}
            }});

            if (sortBy === "gainers") {{
                currentRowsData.sort((a, b) => b[17] - a[17]);
            }} else if (sortBy === "losers") {{
                currentRowsData.sort((a, b) => a[17] - b[17]);
            }} else {{
                currentRowsData.sort((a, b) => b[2] - a[2]);
            }}

            if (currentRowsData.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">कोई डेटा नहीं मिला।</td></tr>';
                return;
            }}

            currentRowsData.slice(0, 200).forEach((r, idx) => {{
                let rankTag = r[18];
                let chgPct = r[17];
                let tagHtml = '';
                let pctStr = chgPct > 0 ? `+${{chgPct.toFixed(2)}}%` : `${{chgPct.toFixed(2)}}%`;
                
                if (rankTag > 0) {{
                    tagHtml = `<div class="rank-slanted-box fraction-gainer"><span>${{getSuffix(rankTag)}}</span><span>${{pctStr}}</span></div>`;
                }} else if (rankTag < 0) {{
                    tagHtml = `<div class="rank-slanted-box fraction-loser"><span>${{getSuffix(Math.abs(rankTag))}}</span><span>${{pctStr}}</span></div>`;
                }} else {{
                    let colorClass = chgPct >= 0 ? 'color:#16a34a; font-weight:bold;' : 'color:#dc2626; font-weight:bold;';
                    tagHtml = `<span style="${{colorClass}}">${{pctStr}}</span>`;
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

            const symbol = r[1];
            const currentDate = r[0];

            document.getElementById("mSymbol").innerText = symbol;
            document.getElementById("mSectorBadge").innerText = r[19];

            let indicesList = r[20].split(', ');
            document.getElementById("mIndexBadges").innerHTML = indicesList.map(idx => `<span class="badge-index">${{idx}}</span>`).join('');
            document.getElementById("mDateTag").innerHTML = `<span style="font-size: 11px; color: #64748b;">${{currentDate}}</span>`;

            // OHLC Values
            document.getElementById("mOpen").innerText = `₹${{r[21].toFixed(2)}}`;
            document.getElementById("mHigh").innerText = `₹${{r[22].toFixed(2)}}`;
            document.getElementById("mLow").innerText = `₹${{r[23].toFixed(2)}}`;
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

            // History Table
            const histList = stockHistory[symbol] || [];
            let currIdx = histList.findIndex(h => h.date === currentDate);
            if (currIdx === -1) currIdx = histList.length - 1;

            let startIdx = Math.max(0, currIdx - 6);
            let recent7Days = histList.slice(startIdx, currIdx + 1).reverse();

            let histBuffer = "";
            recent7Days.forEach(h => {{
                let pctColor = h.chg_pct >= 0 ? '#16a34a' : '#dc2626';
                let pctStr = h.chg_pct > 0 ? `+${{h.chg_pct}}%` : `${{h.chg_pct}}%`;
                histBuffer += `<tr>
                    <td><b>${{h.date}}</b></td>
                    <td class="num">${{h.open}} / ${{h.high}} / ${{h.low}} / <b>${{h.close}}</b></td>
                    <td class="num">${{h.deliv.toLocaleString()}}</td>
                    <td class="num" style="color:${{pctColor}}; font-weight:bold;">${{pctStr}}</td>
                    <td class="num"><b style="color:#10b981;">${{h.spike}}x</b></td>
                </tr>`;
            }});

            document.getElementById("mHistoryBody").innerHTML = histBuffer;
            document.getElementById("detailsModal").style.display = "flex";
        }}

        function hideModal() {{ document.getElementById("detailsModal").style.display = "none"; }}
        function closeModal(event) {{ if (event.target.id === "detailsModal") hideModal(); }}

        function filterTable() {{
            let input = document.getElementById("searchInput").value.toUpperCase();
            let tr = document.getElementById("tableBody").getElementsByTagName("tr");
            for (let i = 0; i < tr.length; i++) {{
                let tdSymbol = tr[i].getElementsByTagName("td")[1];
                if (tdSymbol) {{
                    let text = tdSymbol.textContent || tdSymbol.innerText;
                    tr[i].style.display = text.toUpperCase().indexOf(input) > -1 ? "" : "none";
                }}
            }}
        }}

        function sortTable(n, isNumeric = false) {{
            let table = document.getElementById("screenerTable");
            let rows = Array.from(table.rows).slice(1);
            let dir = table.dataset.sortDir === "asc" ? "desc" : "asc";
            table.dataset.sortDir = dir;

            rows.sort((a, b) => {{
                let x = a.cells[n].innerText.replace(/,/g, '').replace('%', '').replace('x', '').replace('+', '').trim();
                let y = b.cells[n].innerText.replace(/,/g, '').replace('%', '').replace('x', '').replace('+', '').trim();
                return isNumeric ? (dir === "asc" ? parseFloat(x) - parseFloat(y) : parseFloat(y) - parseFloat(x)) : (dir === "asc" ? x.localeCompare(y) : y.localeCompare(x));
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

    print("✅ `index.html` सफलतापूर्वक तैयार हो गया है!")

if __name__ == "__main__":
    generate_delivery_screener()
