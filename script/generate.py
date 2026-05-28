print("🚀 終極版日曆腳本啟動，正在載入工具包...")
import pandas as pd
import os
import glob
import re
from collections import defaultdict

ETF_MAPPING = {
    "00403A": "統一升級50",
    "00981A": "統一台股增長",
    "00988A": "統一全球創新",
    "00991A": "復華未來50",
    "00992A": "群益科技"
}

def robust_load(filepath):
    try:
        all_sheets = pd.read_excel(filepath, sheet_name=None)
        return pd.concat(all_sheets.values(), ignore_index=True)
    except: pass
    try: return pd.read_csv(filepath, encoding='utf-8')
    except: pass
    try: return pd.read_csv(filepath, encoding='big5')
    except: return None

def find_col(columns, keywords):
    for c in columns:
        if any(k in str(c).lower() for k in keywords): return c
    return columns[0]

def generate():
    os.makedirs('dist', exist_ok=True)
    all_files = [f for f in glob.glob(os.path.join('data', "*")) if not os.path.basename(f).startswith('.')]
    
    if not all_files:
        print("❌ data/ 資料夾內沒有檔案！")
        return

    # 🌟 升級 1：改用「日期」做為第一層分類！
    # 結構：date_groups[日期串][ETF代號] = [檔案路徑]
    date_groups = defaultdict(lambda: defaultdict(list))
    
    for f in all_files:
        basename = os.path.basename(f)
        
        # 智慧抓日期：找 8 位數數字 (如 20260527)
        date_match = re.search(r'(\d{8})', basename)
        file_date = date_match.group(1) if date_match else "未分類日期"
        
        # 智慧抓 ETF 代號
        etf_match = re.search(r'(00\d{3}[A-Za-z]?)', basename)
        etf_code = etf_match.group(1).upper() if etf_match else "OTHER"
        
        date_groups[file_date][etf_code].append(f)

    # 紀錄所有成功產出的日期，用來做首頁選單
    available_dates = sorted(list(date_groups.keys()), reverse=True)

    # 讀取標準網頁範本
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        html_template = f.read()

    # 🌟 升級 2：幫每一天產出一個獨立的 .html
    for current_date in available_dates:
        print(f"📅 正在編織日曆：處理 {current_date} 的數據...")
        etf_blocks_html = ""
        
        # 依序處理這一天裡面的每一檔 ETF
        for prefix, files in sorted(date_groups[current_date].items()):
            valid_dfs = [robust_load(f) for f in files if robust_load(f) is not None]
            if not valid_dfs: continue
                
            master_df = pd.concat(valid_dfs, ignore_index=True)
            master_df.columns = [str(c).strip() for c in master_df.columns]

            col_code = find_col(master_df.columns, ['代', 'code'])
            col_name = find_col(master_df.columns, ['名', 'name'])
            col_qty  = find_col(master_df.columns, ['股', '張', 'qty'])

            buy_html, sell_html = "", ""
            buy_count, sell_count = 0, 0

            for _, row in master_df.iterrows():
                if pd.isna(row[col_code]) or pd.isna(row[col_qty]): continue
                code_str = str(row[col_code]).strip()
                if '元' in code_str or '總數' in code_str or '交易' in code_str or '現金' in code_str or code_str == 'nan': continue
                    
                try:
                    raw_qty = float(str(row[col_qty]).replace(',', '').replace('"', ''))
                    is_buy = raw_qty > 0
                    abs_qty = abs(int(raw_qty))
                    qty_val = f"+{abs_qty:,}" if is_buy else f"-{abs_qty:,}"
                except: continue 

                item_html = f'''
                <li class="list-item">
                    <div class="item-left"><span class="col-id">{row[col_code]}</span><div class="name-wrapper"><span class="col-name">{row[col_name]}</span></div></div>
                    <span class="col-qty {'val-buy' if is_buy else 'val-sell'}">{qty_val}</span>
                </li>
                '''
                if is_buy:
                    buy_html += item_html
                    buy_count += 1
                else:
                    sell_html += item_html
                    sell_count += 1

            if not buy_html: buy_html = '<div class="empty-row">- 今日無買進動作 -</div>'
            if not sell_html: sell_html = '<div class="empty-row">- 今日無賣出動作 -</div>'

            etf_name = ETF_MAPPING.get(prefix, "其他投信成分股")

            # 串接這一天裡的所有 ETF 區塊
            etf_blocks_html += f'''
            <div class="etf-section">
                <div class="etf-title"><span>{prefix}</span> {etf_name}</div>
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

        # 🌟 升級 3：打造上方日期切換日曆選單的 HTML
        menu_html = '<div class="date-menu">'
        for d in available_dates:
            # 格式化日期顯示，例如 20260527 變成 05/27
            display_date = f"{d[4:6]}/{d[6:8]}" if len(d) == 8 else d
            active_class = "active" if d == current_date else ""
            # 點擊按鈕直接跳轉到該日期的網頁
            menu_html += f'<a href="{d}.html" class="menu-btn {active_class}">{display_date}</a>'
        menu_html += '</div>'

        # 將日曆選單與當天內容結合
        full_page_content = menu_html + etf_blocks_html

        # 替換日期徽章與主內容
        page_final = html_template.replace('<div class="date-badge">資料更新完畢</div>', f'<div class="date-badge">更新日期：{current_date[:4]}/{current_date[4:6]}/{current_date[6:8]}</div>')
        page_final = page_final.replace('<div id="content"></div>', full_page_content)
        
        # 寫入每日獨立檔案，例如 dist/20260527.html
        with open(f'dist/{current_date}.html', 'w', encoding='utf-8') as f:
            f.write(page_final)

    # 🌟 升級 4：永遠複製最新一天的網頁，作為總首頁 index.html
    if available_dates:
        latest_date = available_dates[0]
        with open(f'dist/{latest_date}.html', 'r', encoding='utf-8') as sf:
            latest_content = sf.read()
        with open('dist/index.html', 'w', encoding='utf-8') as df:
            df.write(latest_content)
        print(f"✨ 總首頁 index.html 已自動同步至最新日期 ({latest_date})")

if __name__ == "__main__":
    generate()