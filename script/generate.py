import pandas as pd
import os
import glob
import re
from collections import defaultdict

# 🌟 設定連續圖要顯示的歷史天數
CHART_DAYS = 30

ETF_MAPPING = {
    "00403A": "統一升級50", "00981A": "統一台股增長", "00988A": "統一全球創新",
    "00991A": "復華未來50", "00992A": "群益科技",
    "00405A": "富邦台灣龍耀", "00402A": "安聯美國科技",
    "00406A": "中信台灣收益成長",
    "00997A": "群益美國增長" # 🌟 新增群益美國增長
}

STOCK_NAME_MAP = {
    "NVDA": "輝達", "AAPL": "蘋果", "MSFT": "微軟", "AMZN": "亞馬遜", 
    "GOOGL": "谷歌", "META": "臉書", "TSLA": "特斯拉", "AMD": "超微", 
    "AVGO": "博通", "TXN": "德儀", "QCOM": "高通", "MU": "美光", 
    "INTC": "英特爾", "CRWD": "資安雲", "ASML": "艾司摩爾",
    "SNDK": "閃迪", "WDC": "威騰", "IFX": "英飛凌", "BE": "布魯姆能源", 
    "DDOG": "資料狗", "AXTI": "AXT", "MRVL": "邁威爾", "LITE": "朗美通",
    "6857": "愛德萬", "7011": "三菱重工", "9984": "軟銀", "8035": "東京威力", 
    "285A": "鎧俠", "6787": "名幸電子", "6981": "村田製作", "009150": "三星電機",
    "688146": "中芯", "SMIC": "中芯", "603256": "宏和電子"
}

# 🌟 內嵌完美版 HTML 範本，徹底根絕範本被汙染的風險
BASE_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETF 成分股變動追蹤</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f4f6f8; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 5px; }
        .date-badge { text-align: center; background-color: #3498db; color: white; padding: 5px 15px; border-radius: 20px; display: inline-block; margin: 0 auto 20px auto; font-size: 14px; }
        .header-wrapper { text-align: center; margin-bottom: 30px; }
        .date-menu { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; align-items: center; position: relative; z-index: 50; margin-bottom: 30px; }
        .menu-btn { display: inline-block; padding: 8px 16px; background-color: #fff; border: 1px solid #ddd; border-radius: 20px; text-decoration: none; color: #555; transition: all 0.2s; font-weight: bold; font-size: 14px; }
        .menu-btn.active, .menu-btn:hover { background-color: #2c3e50; color: #fff; border-color: #2c3e50; }
        .etf-section { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .etf-title { font-size: 22px; font-weight: bold; margin-bottom: 20px; color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
        .etf-title span { color: #e74c3c; margin-right: 4px; }
        .tables-grid { display: flex; gap: 20px; }
        .table-box { flex: 1; border: 1px solid #eaeaea; border-radius: 8px; overflow: hidden; min-width: 0; }
        .box-header { display: flex; justify-content: space-between; padding: 12px 15px; font-weight: bold; color: #fff; font-size: 15px; }
        .header-buy { background-color: #e74c3c; }
        .header-sell { background-color: #2ecc71; }
        .val-buy { color: #e74c3c; }
        .val-sell { color: #2ecc71; }
        @media (max-width: 768px) { .tables-grid { flex-direction: column; } }
        details>summary{list-style:none;cursor:pointer;background:#f8fafc;border:1px solid #94a3b8;color:#475569;padding:6px 12px;border-radius:20px;font-size:14px;font-weight:bold;} 
        details>summary::-webkit-details-marker{display:none;} 
        .more-dates-dropdown{position:absolute;top:100%;left:0;margin-top:8px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;box-shadow:0 10px 25px rgba(0,0,0,0.1);padding:16px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;z-index:100;min-width:320px;}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-wrapper">
            <h1>ETF 成分股變動追蹤</h1>
            <div class="date-badge">看板更新日期：{REPORT_DATE}</div>
        </div>
        {MENU_HTML}
        {CONTENT}
    </div>
</body>
</html>
"""

def find_header_row(df):
    for i in range(min(50, len(df))): 
        # 🌟 超微距標題掃描雷達：不限欄位數，只看「代號」與「數量/權重」的關鍵字組合
        row_str = "".join([str(x) for x in df.iloc[i].values if pd.notna(x)]).lower().replace(' ', '').replace('\n', '')
        
        has_code = ('代' in row_str or 'code' in row_str)
        # 精準鎖定持股資料一定會有的數值標題
        has_target = any(k in row_str for k in ['權重', '比例', '股數', '數量', 'qty', 'weight', '%', '佔', '金額', '張', '持股'])
        
        if has_code and has_target:
            return i
    return -1

def smart_read_and_clean(filepaths):
    fund_size, st_wt_raw, ca_wt_raw = "", None, None
    all_clean_data = []
    
    for filepath in filepaths:
        if os.path.basename(filepath).startswith('~$'): continue
        try:
            if filepath.endswith('.csv'):
                try: df_raw = pd.read_csv(filepath, encoding='utf-8', header=None, sep=None, engine='python')
                except:
                    try: df_raw = pd.read_csv(filepath, encoding='big5', header=None, sep=None, engine='python')
                    except: df_raw = pd.read_csv(filepath, encoding='cp950', header=None, sep=None, engine='python')
                sheets = {'Sheet1': df_raw}
            else:
                try: sheets = pd.read_excel(filepath, sheet_name=None, header=None)
                except Exception:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f: html_content = f.read()
                        dfs = pd.read_html(html_content)
                        sheets = {f'Sheet{i}': df for i, df in enumerate(dfs)}
                    except Exception:
                        try: 
                            df_raw = pd.read_csv(filepath, encoding='utf-8', header=None, sep=None, engine='python')
                            sheets = {'Sheet1': df_raw}
                        except:
                            try:
                                df_raw = pd.read_csv(filepath, encoding='big5', header=None, sep=None, engine='python')
                                sheets = {'Sheet1': df_raw}
                            except: continue

            for sheet_name, df in sheets.items():
                look_for_fund = False
                for i in range(min(30, len(df))):
                    row_vals = [str(x).strip().replace(',', '') for x in df.iloc[i].values if pd.notna(x)]
                    row_str = "".join(row_vals)
                    
                    if not fund_size:
                        if any(k in row_str for k in ['規模', '淨資產', '資產淨值', '資產價值', '淨值總額']):
                            look_for_fund = True
                        
                        if look_for_fund:
                            vals = re.findall(r'\d+\.?\d*', row_str)
                            for v in vals:
                                try:
                                    val = float(v)
                                    if val > 10000000: 
                                        fund_size = f"{val / 100000000:.2f} 億"
                                        look_for_fund = False
                                        break
                                except: pass

                    if '股票' in row_vals or '基金投資股票' in row_str:
                        for v in row_vals:
                            if '%' in v:
                                try: st_wt_raw = float(re.sub(r'[^\d\.]', '', v))
                                except: pass
                    if '現金' in row_vals or '銀行存款' in row_str:
                        for v in row_vals:
                            if '%' in v:
                                try: ca_wt_raw = float(re.sub(r'[^\d\.]', '', v))
                                except: pass

                header_idx = find_header_row(df)
                if header_idx == -1: continue 

                # 🌟 修復致命錯誤：把這行記憶欄位標題的程式碼補回來！！！
                df.columns = df.iloc[header_idx].astype(str)

                # 切斷期權與保證金
                end_idx = len(df)
                for j in range(header_idx + 1, len(df)):
                    row_str = "".join([str(x) for x in df.iloc[j].values if pd.notna(x)]).replace(' ', '')
                    if any(k in row_str for k in ['期貨代碼', '商品代碼', '保證金', '選擇權', '期貨']):
                        end_idx = j
                        break
                
                df = df.iloc[header_idx+1:end_idx].reset_index(drop=True)

                col_code, col_name, col_qty, col_weight = None, None, None, None
                for c in df.columns:
                    c_str = str(c).lower().strip().replace(' ', '').replace('\n', '')
                    if not col_code and ('代' in c_str or 'code' in c_str): col_code = c
                    elif not col_name and ('名' in c_str or 'name' in c_str): col_name = c
                    elif not col_qty and ('股' in c_str or '張' in c_str or 'qty' in c_str or '數量' in c_str) and '權' not in c_str and '%' not in c_str: col_qty = c
                    elif not col_weight and ('權' in c_str or '比' in c_str or '%' in c_str or 'weight' in c_str): col_weight = c

                if not (col_code and col_qty): continue

                cols_to_keep = [col_code, col_qty]
                if col_name: cols_to_keep.append(col_name)
                if col_weight: cols_to_keep.append(col_weight)

                clean_df = df[cols_to_keep].copy()
                clean_df = clean_df.rename(columns={col_code: 'Code', col_qty: 'Qty'})
                if col_name: clean_df = clean_df.rename(columns={col_name: 'Name'})
                else: clean_df['Name'] = ""
                
                if col_weight:
                    clean_df = clean_df.rename(columns={col_weight: 'Weight'})
                    clean_df['Weight'] = clean_df['Weight'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                    clean_df['Weight'] = pd.to_numeric(clean_df['Weight'], errors='coerce').fillna(0)
                    if 0 < clean_df['Weight'].sum() <= 2: clean_df['Weight'] = clean_df['Weight'] * 100
                else: clean_df['Weight'] = 0.0

                clean_df = clean_df.dropna(subset=['Code'])
                clean_df['Qty'] = clean_df['Qty'].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                clean_df['Qty'] = pd.to_numeric(clean_df['Qty'], errors='coerce')
                clean_df = clean_df.dropna(subset=['Qty'])
                all_clean_data.append(clean_df)
        except Exception: pass

    if all_clean_data:
        combined = pd.concat(all_clean_data, ignore_index=True)
        return combined.groupby(['Code', 'Name'], as_index=False).agg({'Qty': 'sum', 'Weight': 'sum'}), fund_size, st_wt_raw, ca_wt_raw
    return None, fund_size, st_wt_raw, ca_wt_raw

def generate():
    print(f"▶ 啟動 ETF 報表產出工具 (無依賴內嵌引擎終極版)...")
    os.makedirs('dist', exist_ok=True)
    all_files = [f for f in glob.glob(os.path.join('data', "*")) if not os.path.basename(f).startswith('.')]
    if not all_files:
        print("❌ 錯誤：找不到任何原始檔案！")
        return

    etf_history = defaultdict(lambda: defaultdict(list))
    all_dates = set()
    for f in all_files:
        basename = os.path.basename(f)
        date_match = re.search(r'(\d{8})', basename)
        etf_match = re.search(r'([0-9]{3,6}[A-Za-z]?)', basename)
        if date_match and etf_match:
            date_str = date_match.group(1)
            raw_code = etf_match.group(1).upper()
            etf_code = "00" + raw_code.lstrip('0') if len(raw_code.lstrip('0')) <= 4 else raw_code 
            etf_history[etf_code][date_str].append(f)
            all_dates.add(date_str)

    sorted_dates = sorted(list(all_dates), reverse=True)
    trend_cache = defaultdict(dict)

    for target_date in sorted_dates:
        print(f"⚙️ 正在建構 [{target_date}] 的報表與走勢圖...")
        etf_blocks_html = ""
        macro_rows_html = "" 

        for etf_code, dates_files in sorted(etf_history.items()):
            available_dates = sorted([d for d in dates_files.keys() if d <= target_date], reverse=True)
            if not available_dates: continue 
                
            actual_date = available_dates[0]
            res_today = smart_read_and_clean(dates_files[actual_date])
            if res_today[0] is None: continue

            df_today, size_today, st_wt_raw, ca_wt_raw = res_today
            
            has_yest = len(available_dates) >= 2
            if has_yest:
                res_yest = smart_read_and_clean(dates_files[available_dates[1]])
                df_yest, _, st_wt_yest_raw, _ = res_yest
            else:
                df_yest, st_wt_yest_raw = None, None

            valid_holdings = df_today[~df_today['Code'].astype(str).str.contains('元|現金|nan|小計|合計|總計', case=False, na=False)]
            st_wt = st_wt_raw if st_wt_raw is not None else valid_holdings['Weight'].sum()
            ca_wt = ca_wt_raw if ca_wt_raw is not None else (max(0, 100.0 - st_wt) if st_wt > 0 else 0)
            
            trend_cache[etf_code][actual_date] = st_wt

            if has_yest and df_yest is not None:
                valid_holdings_yest = df_yest[~df_yest['Code'].astype(str).str.contains('元|現金|nan|小計|合計|總計', case=False, na=False)]
                st_wt_yest = st_wt_yest_raw if st_wt_yest_raw is not None else valid_holdings_yest['Weight'].sum()
                weight_diff = st_wt - st_wt_yest
                diff_sign = "+" if weight_diff >= 0 else ""
                if weight_diff > 0.05: action_badge = f'<span style="color: #166534; font-weight: bold;">加碼 {diff_sign}{weight_diff:.2f}% 📈</span>'
                elif weight_diff < -0.05: action_badge = f'<span style="color: #991b1b; font-weight: bold;">減碼 {diff_sign}{weight_diff:.2f}% 📉</span>'
                else: action_badge = '<span style="color: #475569;">水位持平 ⚖️</span>'
            else:
                action_badge = '<span style="color: #64748b; font-style: italic;">無對比資料</span>'

            date_tag = f'<span style="font-size: 13px; color: #ef4444; margin-left: 8px;">(資料: {actual_date[4:6]}/{actual_date[6:8]})</span>' if actual_date != target_date else ""
            size_badge = f'<span style="font-size: 14px; font-weight: 600; color: #0f172a; margin-left: 12px; background: #e2e8f0; padding: 4px 10px; border-radius: 20px;">規模: {size_today}</span>' if size_today else ""
            ratio_badge = f'<span style="font-size: 14px; font-weight: 600; color: #166534; margin-left: 8px; background: #dcfce7; padding: 4px 10px; border-radius: 20px;">總持股 {st_wt:.2f}% | 現金 {ca_wt:.2f}%</span>' if st_wt > 0 else ""

            etf_name = ETF_MAPPING.get(etf_code, "其他投信成分股")
            macro_rows_html += f'''
            <tr style="border-bottom: 1px solid #e2e8f0; height: 45px; font-size: 15px; white-space: nowrap;">
                <td style="padding: 10px; font-family: monospace; font-weight: bold; color: #1e293b;">{etf_code}</td>
                <td style="padding: 10px; font-weight: 700; color: #334155; text-align: left;">{etf_name} {date_tag}</td>
                <td style="padding: 10px; text-align: right; color: #475569; font-weight: 600;">{size_today or '-'}</td>
                <td style="padding: 10px; text-align: right; color: #0284c7; font-weight: 700;">{st_wt:.2f}%</td>
                <td style="padding: 10px; text-align: right; color: #16a34a; font-weight: 700;">{ca_wt:.2f}%</td>
                <td style="padding: 10px; text-align: right;">{action_badge}</td>
            </tr>
            '''

            chart_labels = []
            chart_data = []
            chart_dates = list(available_dates) 
            chart_dates.reverse() 
            
            for cd in chart_dates:
                if cd not in trend_cache[etf_code]:
                    res_c = smart_read_and_clean(dates_files[cd])
                    if res_c[0] is not None:
                        df_c, sz_c, st_raw_c, ca_raw_c = res_c
                        vh_c = df_c[~df_c['Code'].astype(str).str.contains('元|現金|nan|小計|合計|總計', case=False, na=False)]
                        trend_cache[etf_code][cd] = st_raw_c if st_raw_c is not None else vh_c['Weight'].sum()
                    else:
                        trend_cache[etf_code][cd] = 0
                        
                st_val = trend_cache[etf_code][cd]
                if st_val > 0:
                    chart_labels.append(f"'{cd[4:6]}/{cd[6:8]}'")
                    chart_data.append(f"{st_val:.2f}")

            chart_html = ""
            if len(chart_data) > 1:
                chart_id = f"chart_{etf_code}_{target_date}"
                chart_html = f'''
                <details style="margin-top: 15px; margin-bottom: 15px; outline: none;">
                    <summary style="cursor: pointer; color: #0284c7; font-weight: bold; font-size: 15px; padding: 10px 15px; background: #f0f9ff; border-radius: 8px; border: 1px dashed #7dd3fc; list-style: none; display: inline-block;">
                        📈 點擊展開：持股水位連續走勢圖
                    </summary>
                    <div style="margin-top: 10px; padding: 15px; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
                        
                        <div style="text-align: right; margin-bottom: 10px;">
                            <label style="font-size: 14px; font-weight: bold; color: #475569; margin-right: 8px;">選擇走勢區間：</label>
                            <select id="select_{chart_id}" onchange="updateChart_{chart_id}(this.value)" style="padding: 6px 12px; border-radius: 6px; border: 1px solid #cbd5e1; font-family: inherit; font-size: 14px; cursor: pointer; background-color: #f8fafc;">
                                <option value="all" selected>全部歷史 (從有紀錄至今)</option>
                                <option value="10">近 10 日</option>
                                <option value="30">近 30 日</option>
                                <option value="60">近 60 日</option>
                            </select>
                        </div>

                        <div style="position: relative; height: 250px; width: 100%;">
                            <canvas id="{chart_id}"></canvas>
                        </div>
                    </div>
                </details>
                <script>
                const allLabels_{chart_id} = [{','.join(chart_labels)}];
                const allData_{chart_id} = [{','.join(chart_data)}];
                let chartInst_{chart_id} = null;

                function updateChart_{chart_id}(days) {{
                    let labels = allLabels_{chart_id};
                    let data = allData_{chart_id};
                    
                    if (days !== 'all') {{
                        const sliceCount = parseInt(days, 10);
                        labels = labels.slice(-sliceCount);
                        data = data.slice(-sliceCount);
                    }}
                    
                    if (chartInst_{chart_id}) {{
                        chartInst_{chart_id}.destroy();
                    }}
                    
                    const ctx = document.getElementById('{chart_id}').getContext('2d');
                    chartInst_{chart_id} = new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: labels,
                            datasets: [{{
                                label: '總持股比例 (%)',
                                data: data,
                                borderColor: '#0284c7',
                                backgroundColor: 'rgba(2, 132, 199, 0.1)',
                                borderWidth: 2,
                                pointBackgroundColor: '#0ea5e9',
                                pointRadius: 4,
                                fill: true,
                                tension: 0.3
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{ legend: {{ display: false }} }},
                            scales: {{
                                y: {{ 
                                    suggestedMin: Math.min(...data) - 0.5, 
                                    suggestedMax: Math.max(...data) + 0.5 
                                }}
                            }}
                        }}
                    }});
                }}

                document.addEventListener("DOMContentLoaded", function() {{
                    updateChart_{chart_id}('all');
                }});
                </script>
                '''

            top20_html = ""
            for rank, row in enumerate(valid_holdings.sort_values(by=['Weight', 'Qty'], ascending=[False, False]).head(20).itertuples(), 1):
                base_code = str(row.Code).replace('.0', '').strip().split()[0]
                name_display = STOCK_NAME_MAP.get(base_code, str(row.Name))
                weight_str = f"{row.Weight:.2f}%" if row.Weight > 0 else f"{int(row.Qty):,} 股"
                top20_html += f'<tr style="border-bottom: 1px solid #e2e8f0; height: 48px;"><td style="padding: 8px; color: #64748b; font-size: 14px; font-weight: bold; font-style: italic; white-space: nowrap;">#{rank}</td><td style="padding: 8px; font-family: monospace; color: #475569; font-size: 15px; font-weight: 600; white-space: nowrap;">{base_code}</td><td style="padding: 8px; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 700; color: #1e293b; font-size: 16px;">{name_display}</td><td style="padding: 8px; text-align: right; white-space: nowrap; color: #0ea5e9; font-weight: 900; font-size: 16px;">{weight_str}</td></tr>'
            
            top20_block = f'<div class="table-box" style="margin-top: 25px; background-color: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);"><div class="box-header" style="background-color: #334155; color: white; padding: 12px 16px; font-weight: bold; font-size: 16px;">👑 前 20 大持股</div><div><table style="width: 100%; border-collapse: collapse; text-align: left; background-color: #fff; table-layout: fixed;"><thead><tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; height: 40px; color: #475569; font-size: 14px; font-weight: bold;"><th style="padding: 8px; width: 45px; white-space: nowrap;">排行</th><th style="padding: 8px; width: 70px; white-space: nowrap;">代號</th><th style="padding: 8px; text-align: left; white-space: nowrap;">股名</th><th style="padding: 8px; width: 95px; text-align: right; white-space: nowrap;">比例/股數</th></tr></thead><tbody>{top20_html}</tbody></table></div></div>'

            buy_html, sell_html = "", ""
            buy_count, sell_count = 0, 0

            if has_yest and df_yest is not None:
                df_merged = pd.merge(df_today, df_yest, on='Code', how='outer', suffixes=('_T', '_Y')).fillna({'Qty_T': 0, 'Qty_Y': 0})
                df_merged['Diff'] = df_merged['Qty_T'] - df_merged['Qty_Y']
                df_merged['Name'] = df_merged['Name_T'].fillna(df_merged['Name_Y']).fillna("未知名稱")
                df_diff = df_merged[df_merged['Diff'] != 0].copy()
                
                for _, row in df_diff.iterrows():
                    diff_val = int(row['Diff'])
                    is_buy = diff_val > 0
                    abs_qty = abs(diff_val)
                    qty_str = f"+{abs_qty:,}" if is_buy else f"-{abs_qty:,}"
                    
                    base_code = str(row['Code']).replace('.0', '').strip().split()[0]
                    if '元' in base_code or '現金' in base_code or base_code == 'nan': continue

                    is_new = is_buy and (row['Qty_Y'] == 0)
                    name_display = f"<span style='color: #ef4444; font-weight: bold; font-size: 13px; margin-right: 4px;'>[新]</span>{STOCK_NAME_MAP.get(base_code, str(row['Name']))}" if is_new else STOCK_NAME_MAP.get(base_code, str(row['Name']))

                    item_html = f'<tr style="border-bottom: 1px solid #f1f5f9; height: 50px;"><td style="padding: 10px 8px; font-family: monospace; color: #475569; font-size: 15px; font-weight: 600; white-space: nowrap;">{base_code}</td><td style="padding: 10px 8px; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 700; color: #1e293b; font-size: 16px;">{name_display}</td><td style="padding: 10px 8px; text-align: right; font-weight: 900; font-size: 16px; white-space: nowrap;" class="{"val-buy" if is_buy else "val-sell"}">{qty_str}</td></tr>'
                    if is_buy: buy_html += item_html; buy_count += 1
                    else: sell_html += item_html; sell_count += 1

            if not buy_html: buy_html = '<tr><td colspan="3" style="text-align: center; padding: 20px; color: #94a3b8; font-size: 14px;">- 無異動資料 -</td></tr>'
            if not sell_html: sell_html = '<tr><td colspan="3" style="text-align: center; padding: 20px; color: #94a3b8; font-size: 14px;">- 無異動資料 -</td></tr>'

            table_head = '<div><table style="width: 100%; border-collapse: collapse; text-align: left; background-color: #fff; table-layout: fixed;"><thead><tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; height: 40px; color: #475569; font-size: 14px; font-weight: bold;"><th style="padding: 8px; width: 75px; white-space: nowrap;">代號</th><th style="padding: 8px; text-align: left; white-space: nowrap;">股名</th><th style="padding: 8px; width: 110px; text-align: right; white-space: nowrap;">異動股數</th></tr></thead><tbody>'
            
            etf_blocks_html += f'<div class="etf-section"><div class="etf-title"><span>{etf_code}</span> {etf_name} {date_tag} {size_badge} {ratio_badge}</div>{chart_html}<div class="tables-grid"><div class="table-box"><div class="box-header header-buy">買進成分股 (共 {buy_count} 檔)</div>{table_head}{buy_html}</tbody></table></div></div><div class="table-box"><div class="box-header header-sell">賣出成分股 (共 {sell_count} 檔)</div>{table_head}{sell_html}</tbody></table></div></div></div>{top20_block}</div>'

        macro_dashboard_html = ""
        if macro_rows_html:
            macro_dashboard_html = f'''
            <div class="macro-dashboard" style="margin-top: 20px; margin-bottom: 35px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <h2 style="margin-top: 0; color: #0f172a; font-size: 18px; margin-bottom: 15px;">📊 經理人多空水位大盤看板 (自動抓取最新)</h2>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; min-width: 750px;">
                        <thead>
                            <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1; height: 42px; color: #334155; font-size: 14px; font-weight: bold; white-space: nowrap;">
                                <th style="padding: 10px; width: 95px;">ETF 代號</th>
                                <th style="padding: 10px; text-align: left;">ETF 名稱</th>
                                <th style="padding: 10px; width: 110px; text-align: right;">基金規模</th>
                                <th style="padding: 10px; width: 110px; text-align: right;">股票比重</th>
                                <th style="padding: 10px; width: 110px; text-align: right;">現金比重</th>
                                <th style="padding: 10px; width: 160px; text-align: right;">操盤動態</th>
                            </tr>
                        </thead>
                        <tbody>{macro_rows_html}</tbody>
                    </table>
                </div>
            </div>
            '''

        if not etf_blocks_html: 
            etf_blocks_html = '<div style="color:#8898aa; padding: 30px; text-align:center; font-style:italic; font-size: 16px;">無資料</div>'

        menu_html = '<div class="date-menu">'
        for idx, d in enumerate(sorted_dates): 
            btn = f'<a href="{d}.html" class="menu-btn {"active" if d == target_date else ""}">{d[4:6]}/{d[6:8]}</a>'
            if idx < 5: menu_html += btn
            elif idx == 5: menu_html += f'<details style="position:relative; display:inline-block;"><summary>歷史紀錄 ▾</summary><div class="more-dates-dropdown">{btn}'
            else: menu_html += btn
        if len(sorted_dates) > 5: menu_html += '</div></details>'
        menu_html += '</div>'

        full_page = BASE_HTML.replace('{REPORT_DATE}', f'{target_date[:4]}/{target_date[4:6]}/{target_date[6:8]}')
        full_page = full_page.replace('{MENU_HTML}', menu_html)
        full_page = full_page.replace('{CONTENT}', macro_dashboard_html + etf_blocks_html)

        with open(f'dist/{target_date}.html', 'w', encoding='utf-8') as f: 
            f.write(full_page)

    if sorted_dates and os.path.exists(f'dist/{sorted_dates[0]}.html'):
        with open(f'dist/{sorted_dates[0]}.html', 'r', encoding='utf-8') as sf, open('dist/index.html', 'w', encoding='utf-8') as df: 
            df.write(sf.read())
        print(f"✨ 報表全數產出完畢！")

if __name__ == "__main__":
    generate()