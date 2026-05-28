print("🚀 程式已成功啟動，正在載入工具包...")
import pandas as pd
import os
import glob
import re  # 🌟 新增：用來自動辨識檔名裡的 ETF 代號
from collections import defaultdict

# 建立 ETF 代號與名稱的對照表
ETF_MAPPING = {
    "00403A": "統一升級50",
    "00981A": "統一台股增長",
    "00988A": "統一全球創新",
    "00991A": "復華未來50",
    "00992A": "群益科技"  # 已經為您改成簡短名稱
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

    # 🌟 核心升級：智慧尋找檔名中的 ETF 代號 (例如 00991A, 00992A)
    grouped_files = defaultdict(list)
    for f in all_files:
        basename = os.path.basename(f)
        # 用正則表達式尋找：00 開頭，接3個數字，最後可能有一個英文字母
        match = re.search(r'(00\d{3}[A-Za-z]?)', basename)
        if match:
            prefix = match.group(1).upper() # 成功抓到如 "00991A"
        else:
            # 如果檔名裡真的沒有代號，才退而求其次抓前面的字
            prefix = basename.split('_')[0] if '_' in basename else basename[:6]
            
        grouped_files[prefix].append(f)

    final_content = ""

    # 開始針對每一檔 ETF 獨立處理
    for prefix, files in grouped_files.items():
        print(f"🔄 正在獨立處理 ETF: {prefix} (共 {len(files)} 個檔案)")
        valid_dfs = [robust_load(f) for f in files if robust_load(f) is not None]
        if not valid_dfs: continue
            
        master_df = pd.concat(valid_dfs, ignore_index=True)
        master_df.columns = [str(c).strip() for c in master_df.columns]

        col_code = find_col(master_df.columns, ['代', 'code'])
        col_name = find_col(master_df.columns, ['名', 'name'])
        col_qty  = find_col(master_df.columns, ['股', '張', 'qty'])

        buy_html = ""
        sell_html = ""
        buy_count = 0
        sell_count = 0

        for _, row in master_df.iterrows():
            if pd.isna(row[col_code]) or pd.isna(row[col_qty]): continue
            code_str = str(row[col_code]).strip()
            if '元' in code_str or '總數' in code_str or '交易' in code_str or '現金' in code_str or code_str == 'nan': continue
                
            try:
                raw_qty = float(str(row[col_qty]).replace(',', '').replace('"', ''))
                is_buy = raw_qty > 0
                abs_qty = abs(int(raw_qty))
                qty_val = f"+{abs_qty:,}" if is_buy else f"-{abs_qty:,}"
            except:
                continue 

            item_html = f'''
            <li class="list-item">
                <div class="item-left">
                    <span class="col-id">{row[col_code]}</span>
                    <div class="name-wrapper"><span class="col-name">{row[col_name]}</span></div>
                </div>
                <span class="col-qty {'val-buy' if is_buy else 'val-sell'}">{qty_val}</span>
            </li>
            '''
            
            if is_buy:
                buy_html += item_html
                buy_count += 1
            else:
                sell_html += item_html
                sell_count += 1

        if not buy_html: buy_html = '<div class="empty-row">- 今日無資料 -</div>'
        if not sell_html: sell_html = '<div class="empty-row">- 今日無資料 -</div>'

        # 抓取對應的 ETF 名稱
        etf_name = ETF_MAPPING.get(prefix, "其他投信成分股")

        # 為這檔 ETF 生成專屬的獨立區塊
        final_content += f'''
        <div class="etf-section">
            <div class="etf-title"><span>{prefix}</span> {etf_name}</div>
            
            <div class="tables-grid">
                <div class="table-box">
                    <div class="box-header header-buy">
                        <div>買進成分股</div><div>共 {buy_count} 檔</div>
                    </div>
                    <div class="list-header">
                        <div class="list-header-left">
                            <span style="width: 48px; display:inline-block;">代號</span><span>名稱</span>
                        </div>
                        <span>數量</span>
                    </div>
                    <ul class="data-list">
                        {buy_html}
                    </ul>
                </div>

                <div class="table-box">
                    <div class="box-header header-sell">
                        <div>賣出成分股</div><div>共 {sell_count} 檔</div>
                    </div>
                    <div class="list-header">
                        <div class="list-header-left">
                            <span style="width: 48px; display:inline-block;">代號</span><span>名稱</span>
                        </div>
                        <span>數量</span>
                    </div>
                    <ul class="data-list">
                        {sell_html}
                    </ul>
                </div>
            </div>
        </div>
        '''

    with open('templates/index.html', 'r', encoding='utf-8') as f:
        html_template = f.read()
        
    html_final = html_template.replace('<div id="content"></div>', final_content)
    
    with open('dist/index.html', 'w', encoding='utf-8') as f:
        f.write(html_final)
    print("✅ 網頁自動生成成功！多檔 ETF 處理完畢！")

if __name__ == "__main__":
    generate()