print("🚀 終極完全體啟動：自動清洗 + 異步日期 + 正統隱形表格排版 (徹底根除股名垂直與美股失衡)...")
import pandas as pd
import os
import glob
import re
from collections import defaultdict

# 🌟 包含所有 7 檔 ETF 名稱對應表
ETF_MAPPING = {
    "00403A": "統一升級50", "00981A": "統一台股增長", "00988A": "統一全球創新",
    "00991A": "復華未來50", "00992A": "群益科技",
    "00405A": "富邦台灣龍耀", "00402A": "安聯美國科技"
}

def extract_fund_size(df):
    try:
        for i in range(min(20, len(df))):
            row_vals = [str(x).strip().replace(',', '') for x in df.iloc[i].values if pd.notna(x)]
            row_str = " ".join(row_vals)
            
            if any(keyword in row_str for keyword in ['規模', '淨資產', '資產價值', '發行餘額', '資產總額', '總資產', '淨值總額', '基金資產', '總金額']):
                for val_str in row_vals:
                    try:
                        clean_val = re.sub(r'[^\d\.\-eE]', '', val_str)
                        if not clean_val: continue
                        val = float(clean_val)
                        if val > 10000000: return f"{val / 100000000:.2f} 億"
                        elif 0 < val < 100000 and '億' in row_str: return f"{val:.2f} 億"
                    except: pass
                
                if i + 1 < len(df):
                    next_row_vals = [str(x).strip().replace(',', '') for x in df.iloc[i+1].values if pd.notna(x)]
                    for val_str in next_row_vals:
                        try:
                            clean_val = re.sub(r'[^\d\.\-eE]', '', val_str)
                            if not clean_val: continue
                            val = float(clean_val)
                            if val > 10000000: return f"{val / 100000000:.2f} 億"
                        except: pass
    except Exception:
        pass
    return ""

def find_header_row(df):
    for i in range(min(50, len(df))): 
        row_str = "".join(str(x) for x in df.iloc[i].values).lower()
        if ('代' in row_str or 'code' in row_str) and ('股' in row_str or '權重' in row_str or 'qty' in row_str):
            return i
    return -1

def smart_read_and_clean(filepath):
    if os.path.basename(filepath).startswith('~$'): return None, ""

    fund_size = ""
    try:
        if filepath.endswith('.csv'):
            try: df_raw = pd.read_csv(filepath, encoding='utf-8', header=None)
            except: df_raw = pd.read_csv(filepath, encoding='big5', header=None)
            sheets = {'Sheet1': df_raw}
        else:
            try: sheets = pd.read_excel(filepath, sheet_name=None, header=None)
            except Exception as e:
                try: dfs = pd.read_html(filepath, encoding='utf-8', header=None)
                except: dfs = pd.read_html(filepath, encoding='big5', header=None)
                sheets = {f'Sheet{i}': df for i, df in enumerate(dfs)}

        all_clean_data = []
        for sheet_name, df in sheets.items():
            if not fund_size: fund_size = extract_fund_size(df)

            header_idx = find_header_row(df)
            if header_idx == -1: continue 

            df.columns = df.iloc[header_idx].astype(str)
            df = df.iloc[header_idx+1:].reset_index(drop=True)

            col_code, col_name, col_qty, col_weight = None, None, None, None
            for c in df.columns:
                c_str = str(c).lower().strip()
                if not col_code and ('代' in c_str or 'code' in c_str): col_code = c
                elif not col_name and ('名' in c_str or 'name' in c_str): col_name = c
                elif not col_qty and ('股' in c_str or '張' in c_str or 'qty' in c_str) and '權重' not in c_str and '%' not in c_str: col_qty = c
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
                clean_df['Weight'] = pd.to_numeric(clean_df['Weight'].astype(str).str.replace('%', '').str.replace(',', '').str.replace('"', ''), errors='coerce').fillna(0)
                if 0 < clean_df['Weight'].sum() <= 2: clean_df['Weight'] = clean_df['Weight'] * 100
            else:
                clean_df['Weight'] = 0.0

            clean_df = clean_df.dropna(subset=['Code'])
            clean_df['Qty'] = pd.to_numeric(clean_df['Qty'].astype(str).str.replace(',', '').str.replace('"', ''), errors='coerce')
            clean_df = clean_df.dropna(subset=['Qty'])
            all_clean_data.append(clean_df)

        if all_clean_data:
            combined = pd.concat(all_clean_data, ignore_index=True)
            return combined.groupby(['Code', 'Name'], as_index=False).agg({'Qty': 'sum', 'Weight': 'sum'}), fund_size
        return None, ""
    except Exception as e:
        print(f"❌ 讀取失敗 {os.path.basename(filepath)}: {e}")
        return None, ""

def generate():
    os.makedirs('dist', exist_ok=True)
    all_files = [f for f in glob.glob(os.path.join('data', "*")) if not os.path.basename(f).startswith('.')]
    
    if not all_files:
        return

    etf_history = defaultdict(dict)
    all_dates = set()
    
    for f in all_files:
        basename = os.path.basename(f)
        date_match = re.search(r'(\d{8})', basename)
        etf_match = re.search(r'([0-9]{3,6}[A-Za-z]?)', basename)
        
        if date_match and etf_match:
            date_str = date_match.group(1)
            raw_code = etf_match.group(1).upper()
            etf_code = "00" + raw_code.lstrip('0') if len(raw_code.lstrip('0')) <= 4 else raw_code 
            etf_history[etf_code][date_str] = f
            all_dates.add(date_str)

    sorted_dates = sorted(list(all_dates), reverse=True)
    
    valid_report_dates = []
    for target_date in sorted_dates:
        for etf_code, dates_files in etf_history.items():
            if target_date in dates_files:
                available_dates = sorted([d for d in dates_files.keys() if d <= target_date], reverse=True)
                if len(available_dates) >= 2:
                    valid_report_dates.append(target_date)
                    break 

    if not valid_report_dates:
        return

    with open('templates/index.html', 'r', encoding='utf-8') as f:
        html_template = f.read()

    for target_date in valid_report_dates:
        etf_blocks_html = ""
        
        for etf_code, dates_files in sorted(etf_history.items()):
            if target_date not in dates_files:
                continue 
                
            available_dates = sorted([d for d in dates_files.keys() if d <= target_date], reverse=True)
            if len(available_dates) < 2:
                continue 
                
            previous_date = available_dates[1]
            res_today = smart_read_and_clean(dates_files[target_date])
            res_yest = smart_read_and_clean(dates_files[previous_date])
            
            if res_today[0] is None or res_yest[0] is None: 
                continue

            df_today, size_today = res_today
            df_yest, size_yest = res_yest

            size_badge = f'<span style="font-size: 16px; font-weight: 600; color: #0f172a; margin-left: 12px; background: #e2e8f0; padding: 4px 12px; border-radius: 20px; letter-spacing: 0.5px;">規模: {size_today}</span>' if size_today else ""

            top20_df = df_today.sort_values(by=['Weight', 'Qty'], ascending=[False, False])
            valid_holdings = top20_df[~top20_df['Code'].astype(str).str.contains('元|現金|nan|小計|合計|總計', case=False, na=False)]
            top20_items = valid_holdings.head(20)
            
            # 🌟 前 20 大持股改為 Table 排版，徹底根除垂直化！
            top20_html = ""
            for rank, row in enumerate(top20_items.itertuples(), 1):
                code_str = str(row.Code).replace('.0', '')
                name_str = str(row.Name)
                weight_str = f"{row.Weight:.2f}%" if row.Weight > 0 else f"{int(row.Qty):,} 股"
                
                is_us_stock = any(char.isalpha() for char in code_str)
                
                if is_us_stock:
                    name_td_content = ""
                else:
                    name_td_content = f'<span style="font-weight: 700; color: #1e293b; font-size: 17px;">{name_str}</span>'

                top20_html += f'''
                <tr style="border-bottom: 1px solid #e2e8f0; height: 52px;">
                    <td style="padding: 10px 16px; width: 45px; color: #64748b; font-size: 16px; font-weight: bold; font-style: italic;">#{rank}</td>
                    <td style="padding: 10px 8px; width: 85px; font-family: monospace; color: #475569; font-size: 17px; font-weight: 600;">{code_str}</td>
                    <td style="padding: 10px 8px; text-align: left;">{name_td_content}</td>
                    <td style="padding: 10px 16px; text-align: right; width: 100px; color: #0ea5e9; font-weight: 900; font-size: 18px;">{weight_str}</td>
                </tr>
                '''
            
            top20_block = f'''
            <div class="table-box" style="margin-top: 25px; max-width: 100%; background-color: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div class="box-header" style="background-color: #334155; color: white; padding: 14px 20px; font-weight: bold; font-size: 18px;">
                    👑 前 20 大持股 (本日)
                </div>
                <table style="width: 100%; border-collapse: collapse; text-align: left; background-color: #fff;">
                    <thead>
                        <tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; height: 44px; color: #475569; font-size: 16px; font-weight: bold;">
                            <th style="padding: 10px 16px;">排行</th>
                            <th style="padding: 10px 8px;">代號</th>
                            <th style="padding: 10px 8px; text-align: left;">股名</th>
                            <th style="padding: 10px 16px; text-align: right;">比例 / 股數</th>
                        </tr>
                    </thead>
                    <tbody>
                        {top20_html}
                    </tbody>
                </table>
            </div>
            '''

            df_merged = pd.merge(df_today, df_yest, on='Code', how='outer', suffixes=('_T', '_Y'))
            df_merged['Qty_T'] = df_merged['Qty_T'].fillna(0)
            df_merged['Qty_Y'] = df_merged['Qty_Y'].fillna(0)
            df_merged['Diff'] = df_merged['Qty_T'] - df_merged['Qty_Y']
            
            df_merged['Name'] = df_merged['Name_T'].fillna(df_merged['Name_Y']).fillna("未知名稱")
            df_diff = df_merged[df_merged['Diff'] != 0].copy()
            
            if df_diff.empty: 
                etf_name = ETF_MAPPING.get(etf_code, "其他投信成分股")
                etf_blocks_html += f'''
                <div class="etf-section">
                    <div class="etf-title" style="display: flex; align-items: center; flex-wrap: wrap;"><span>{etf_code}</span> {etf_name} {size_badge}</div>
                    <div style="text-align: center; padding: 40px 20px; color: #8898aa; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #dce1e7; font-size: 17px;">
                        ⚖️ 今日成分股無任何買賣變動
                    </div>
                    {top20_block}
                </div>
                '''
                continue

            buy_html, sell_html = "", ""
            buy_count, sell_count = 0, 0

            for _, row in df_diff.iterrows():
                diff_val = int(row['Diff'])
                is_buy = diff_val > 0
                abs_qty = abs(diff_val)
                qty_str = f"+{abs_qty:,}" if is_buy else f"-{abs_qty:,}"
                code_str = str(row['Code']).replace('.0', '')
                
                if '元' in code_str or '現金' in code_str or code_str == 'nan': continue

                is_new_entry = False
                if is_buy and (pd.isna(row['Qty_Y']) or row['Qty_Y'] == 0):
                    is_new_entry = True

                is_us_stock = any(char.isalpha() for char in code_str)
                
                if is_us_stock:
                    name_td_content = f"<span style='color: #ef4444; font-weight: bold; font-size: 14px; margin-right: 6px;'>[新進]</span>" if is_new_entry else ""
                else:
                    name_display = f"<span style='color: #ef4444; font-weight: bold; font-size: 14px; margin-right: 6px;'>[新進]</span>{row['Name']}" if is_new_entry else row['Name']
                    name_td_content = f'<span style="font-weight: 700; color: #1e293b; font-size: 17px;">{name_display}</span>'

                # 🌟 買賣清單改為 Table 每一橫列 🛠️
                item_html = f'''
                <tr style="border-bottom: 1px solid #f1f5f9; height: 52px;">
                    <td style="padding: 10px 16px; width: 85px; font-family: monospace; color: #475569; font-size: 17px; font-weight: 600;">{code_str}</td>
                    <td style="padding: 10px 8px; text-align: left;">{name_td_content}</td>
                    <td style="padding: 10px 16px; text-align: right; width: 120px; font-weight: 900; font-size: 18px;" class="{'val-buy' if is_buy else 'val-sell'}">{qty_str}</td>
                </tr>
                '''
                if is_buy:
                    buy_html += item_html; buy_count += 1
                else:
                    sell_html += item_html; sell_count += 1

            # 🌟 Table 版的無變動提示
            if not buy_html: buy_html = '<tr><td colspan="3" style="text-align: center; padding: 20px; color: #94a3b8; font-size: 16px;">- 今日無買進動作 -</td></tr>'
            if not sell_html: sell_html = '<tr><td colspan="3" style="text-align: center; padding: 20px; color: #94a3b8; font-size: 16px;">- 今日無賣出動作 -</td></tr>'

            # 🌟 重新組裝買進與賣出的 Table 容器
            table_header_template = '''
            <table style="width: 100%; border-collapse: collapse; text-align: left; background-color: #fff;">
                <thead>
                    <tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; height: 44px; color: #475569; font-size: 16px; font-weight: bold;">
                        <th style="padding: 10px 16px;">代號</th>
                        <th style="padding: 10px 8px; text-align: left;">成分股名稱</th>
                        <th style="padding: 10px 16px; text-align: right;">異動股數</th>
                    </tr>
                </thead>
                <tbody>
            '''

            etf_name = ETF_MAPPING.get(etf_code, "其他投信成分股")
            etf_blocks_html += f'''
            <div class="etf-section">
                <div class="etf-title" style="display: flex; align-items: center; flex-wrap: wrap;"><span>{etf_code}</span> {etf_name} {size_badge}</div>
                <div class="tables-grid">
                    <div class="table-box" style="background-color: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <div class="box-header header-buy" style="font-size: 18px; padding: 14px 20px; font-weight: bold;"><div>買進成分股 (共 {buy_count} 檔)</div></div>
                        {table_header_template}
                        {buy_html}
                        </tbody>
                        </table>
                    </div>
                    <div class="table-box" style="background-color: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <div class="box-header header-sell" style="font-size: 18px; padding: 14px 20px; font-weight: bold;"><div>賣出成分股 (共 {sell_count} 檔)</div></div>
                        {table_header_template}
                        {sell_html}
                        </tbody>
                        </table>
                    </div>
                </div>
                {top20_block}
            </div>
            '''

        if etf_blocks_html == "":
            etf_blocks_html = '<div style="color:#8898aa; padding: 30px; text-align:center; font-style:italic; font-size: 17px;">今日各檔 ETF 無成分股變動，或資料不足。</div>'

        menu_html = '<div class="date-menu" style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; position: relative; z-index: 50;">'
        visible_count = 5
        
        for idx, d in enumerate(valid_report_dates): 
            display_date = f"{d[4:6]}/{d[6:8]}"
            active_class = "active" if d == target_date else ""
            btn_html = f'<a href="{d}.html" class="menu-btn {active_class}">{display_date}</a>'
            
            if idx < visible_count:
                menu_html += btn_html
            elif idx == visible_count:
                menu_html += f'''
                <style>
                    details > summary {{ list-style: none; outline: none !important; user-select: none; -webkit-tap-highlight-color: transparent; cursor: pointer; background-color: #f8fafc; border: 1px solid #94a3b8; color: #475569; padding: 6px 12px; border-radius: 20px; font-size: 15px; font-weight: bold; transition: all 0.2s; }}
                    details > summary::-webkit-details-marker {{ display: none; }}
                    details > summary:focus, details > summary:active, details > summary:focus-visible {{ outline: none !important; box-shadow: none !important; border-color: #94a3b8; }}
                    details[open] > summary {{ background-color: #e2e8f0; color: #0f172a; }}
                    .more-dates-dropdown {{ position: absolute; top: 100%; left: 0; margin-top: 8px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1); padding: 16px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; z-index: 100; width: max-content; min-width: 320px; }}
                    @media (max-width: 600px) {{ .more-dates-dropdown {{ grid-template-columns: repeat(3, 1fr); min-width: 280px; left: 0;}} }}
                </style>
                <details style="position: relative;">
                    <summary>歷史紀錄 ▾</summary>
                    <div class="more-dates-dropdown">
                '''
                menu_html += btn_html
            else:
                menu_html += btn_html

        if len(valid_report_dates) > visible_count:
            menu_html += '</div></details>'
        menu_html += '</div>'

        full_page = html_template.replace('<div class="date-badge">資料更新完畢</div>', f'<div class="date-badge">更新日期：{target_date[:4]}/{target_date[4:6]}/{target_date[6:8]}</div>')
        full_page = full_page.replace('<div id="content"></div>', menu_html + etf_blocks_html)
        
        with open(f'dist/{target_date}.html', 'w', encoding='utf-8') as f:
            f.write(full_page)

    latest_date = valid_report_dates[0]
    if os.path.exists(f'dist/{latest_date}.html'):
        with open(f'dist/{latest_date}.html', 'r', encoding='utf-8') as sf:
            with open('dist/index.html', 'w', encoding='utf-8') as df:
                df.write(sf.read())

if __name__ == "__main__":
    generate()