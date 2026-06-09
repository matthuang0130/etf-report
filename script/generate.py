print("🚀 終極完全體啟動：自動清洗 + 自動比對差額 + 網頁產出...")
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

def find_header_row(df):
    for i in range(min(50, len(df))): 
        row_str = "".join(str(x) for x in df.iloc[i].values).lower()
        if ('代' in row_str or 'code' in row_str) and ('股' in row_str or '權重' in row_str or 'qty' in row_str):
            return i
    return -1

def smart_read_and_clean(filepath):
    if os.path.basename(filepath).startswith('~$'):
        return None

    try:
        if filepath.endswith('.csv'):
            try: df_raw = pd.read_csv(filepath, encoding='utf-8', header=None)
            except: df_raw = pd.read_csv(filepath, encoding='big5', header=None)
            sheets = {'Sheet1': df_raw}
        else:
            try:
                sheets = pd.read_excel(filepath, sheet_name=None, header=None)
            except Exception as e:
                # 🌟 破解富邦的「假 Excel 真 HTML」護盾
                try:
                    dfs = pd.read_html(filepath, encoding='utf-8', header=None)
                except:
                    dfs = pd.read_html(filepath, encoding='big5', header=None)
                sheets = {f'Sheet{i}': df for i, df in enumerate(dfs)}

        all_clean_data = []
        for sheet_name, df in sheets.items():
            header_idx = find_header_row(df)
            if header_idx == -1: continue 

            df.columns = df.iloc[header_idx].astype(str)
            df = df.iloc[header_idx+1:].reset_index(drop=True)

            col_code, col_name, col_qty = None, None, None
            for c in df.columns:
                c_str = str(c).lower().strip()
                if not col_code and ('代' in c_str or 'code' in c_str): 
                    col_code = c
                elif not col_name and ('名' in c_str or 'name' in c_str): 
                    col_name = c
                elif not col_qty and ('股' in c_str or '張' in c_str or 'qty' in c_str) and '權重' not in c_str and '%' not in c_str: 
                    col_qty = c

            if not (col_code and col_qty): continue

            clean_df = df[[col_code, col_name, col_qty]].copy() if col_name else df[[col_code, col_qty]].copy()
            clean_df.columns = ['Code', 'Name', 'Qty'] if col_name else ['Code', 'Qty']
            if not col_name: clean_df['Name'] = ""

            clean_df = clean_df.dropna(subset=['Code'])
            clean_df['Qty'] = pd.to_numeric(clean_df['Qty'].astype(str).str.replace(',', '').str.replace('"', ''), errors='coerce')
            clean_df = clean_df.dropna(subset=['Qty'])
            all_clean_data.append(clean_df)

        if all_clean_data:
            combined = pd.concat(all_clean_data, ignore_index=True)
            return combined.groupby(['Code', 'Name'], as_index=False)['Qty'].sum()
        return None
    except Exception as e:
        print(f"❌ 讀取失敗 {os.path.basename(filepath)}: {e}")
        return None

def generate():
    os.makedirs('dist', exist_ok=True)
    all_files = [f for f in glob.glob(os.path.join('data', "*")) if not os.path.basename(f).startswith('.')]
    
    if not all_files:
        print("❌ data/ 資料夾內沒有檔案！")
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
            print(f"📥 成功讀取待命檔案: {etf_code} [{date_str}]")

    sorted_dates = sorted(list(all_dates), reverse=True)
    if len(sorted_dates) < 2:
        print("⚠️ 警告：資料夾內至少需要『兩天』的檔案 才能計算買賣差額喔！")
        return

    with open('templates/index.html', 'r', encoding='utf-8') as f:
        html_template = f.read()

    for i in range(len(sorted_dates) - 1):
        target_date = sorted_dates[i]
        previous_date = sorted_dates[i+1]
        print(f"\n🧮 正在比對 【{target_date}】 與 【{previous_date}】...")
        
        etf_blocks_html = ""
        
        for etf_code, dates_files in sorted(etf_history.items()):
            if target_date not in dates_files or previous_date not in dates_files:
                print(f"    ⏭️ 略過 {etf_code}：因為缺乏兩天的完整檔案。")
                continue 
                
            df_today = smart_read_and_clean(dates_files[target_date])
            df_yest = smart_read_and_clean(dates_files[previous_date])
            
            if df_today is None or df_yest is None: 
                print(f"    ❌ 清洗失敗 {etf_code}：無法解析檔案內容。")
                etf_name = ETF_MAPPING.get(etf_code, "其他投信成分股")
                etf_blocks_html += f'''
                <div class="etf-section">
                    <div class="etf-title"><span>{etf_code}</span> {etf_name}</div>
                    <div style="text-align: center; padding: 40px 20px; color: #e74c3c; background-color: #fdf2f0; border-radius: 8px; border: 1px dashed #fadbd8; font-size: 16px;">
                        ⚠️ 檔案讀取失敗：投信網站提供的資料格式異常，或假日無更新檔案。
                    </div>
                </div>
                '''
                continue

            df_merged = pd.merge(df_today, df_yest, on='Code', how='outer', suffixes=('_T', '_Y'))
            df_merged['Qty_T'] = df_merged['Qty_T'].fillna(0)
            df_merged['Qty_Y'] = df_merged['Qty_Y'].fillna(0)
            df_merged['Diff'] = df_merged['Qty_T'] - df_merged['Qty_Y']
            
            df_merged['Name'] = df_merged['Name_T'].fillna(df_merged['Name_Y']).fillna("未知名稱")
            df_diff = df_merged[df_merged['Diff'] != 0].copy()
            
            if df_diff.empty: 
                print(f"    ⚖️ 無變動 {etf_code}：兩天持股完全一致。")
                etf_name = ETF_MAPPING.get(etf_code, "其他投信成分股")
                etf_blocks_html += f'''
                <div class="etf-section">
                    <div class="etf-title"><span>{etf_code}</span> {etf_name}</div>
                    <div style="text-align: center; padding: 40px 20px; color: #8898aa; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #dce1e7; font-size: 16px;">
                        ⚖️ 今日成分股無任何買賣變動
                    </div>
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

                name_display = f"<span style='color: #ef4444; font-weight: bold; font-size: 12px; margin-right: 4px;'>[新進]</span>{row['Name']}" if is_new_entry else row['Name']

                item_html = f'''
                <li class="list-item">
                    <div class="item-left"><span class="col-id">{code_str}</span><div class="name-wrapper"><span class="col-name">{name_display}</span></div></div>
                    <span class="col-qty {'val-buy' if is_buy else 'val-sell'}">{qty_str}</span>
                </li>
                '''
                if is_buy:
                    buy_html += item_html; buy_count += 1
                else:
                    sell_html += item_html; sell_count += 1

            if not buy_html: buy_html = '<div class="empty-row">- 今日無買進動作 -</div>'
            if not sell_html: sell_html = '<div class="empty-row">- 今日無賣出動作 -</div>'

            etf_name = ETF_MAPPING.get(etf_code, "其他投信成分股")
            etf_blocks_html += f'''
            <div class="etf-section">
                <div class="etf-title"><span>{etf_code}</span> {etf_name}</div>
                <div class="tables-grid">
                    <div class="table-box">
                        <div class="box-header header-buy"><div>買進成分股</div><div>共 {buy_count} 檔</div></div>
                        <div class="list-header"><div class="list-header-left"><span style="width:48px;display:inline-block;">代號</span><span>名稱</span></div><span>數量</span></div>
                        <ul class="data-list">{buy_html}</ul>
                    </div>
                    <div class="table-box">
                        <div class="box-header header-sell"><div>賣出成分股</div><div>共 {sell_count} 檔</div></div>
                        <div class="list-header"><div class="list-header-left"><span style="width:48px;display:inline-block;">代號</span><span>名稱</span></div><span>數量</span></div>
                        <ul class="data-list">{sell_html}</ul>
                    </div>
                </div>
            </div>
            '''
            print(f"  ✅ 成功計算 {etf_code}：買進 {buy_count} 檔，賣出 {sell_count} 檔。")

        if etf_blocks_html == "":
            etf_blocks_html = '<div style="color:#8898aa; padding: 30px; text-align:center; font-style:italic;">今日各檔 ETF 無成分股變動，或資料不足。</div>'

        menu_html = '<div class="date-menu">'
        for d in sorted_dates[:-1]: 
            display_date = f"{d[4:6]}/{d[6:8]}"
            active_class = "active" if d == target_date else ""
            menu_html += f'<a href="{d}.html" class="menu-btn {active_class}">{display_date}</a>'
        menu_html += '</div>'

        full_page = menu_html + etf_blocks_html
        page_final = html_template.replace('<div class="date-badge">資料更新完畢</div>', f'<div class="date-badge">更新日期：{target_date[:4]}/{target_date[4:6]}/{target_date[6:8]}</div>')
        page_final = page_final.replace('<div id="content"></div>', full_page)
        
        with open(f'dist/{target_date}.html', 'w', encoding='utf-8') as f:
            f.write(page_final)

    latest_date = sorted_dates[0]
    if os.path.exists(f'dist/{latest_date}.html'):
        with open(f'dist/{latest_date}.html', 'r', encoding='utf-8') as sf:
            with open('dist/index.html', 'w', encoding='utf-8') as df:
                df.write(sf.read())
        print(f"\n✨ 完美收工！首頁已更新為 {latest_date} 的差額比對報表！")

if __name__ == "__main__":
    generate()