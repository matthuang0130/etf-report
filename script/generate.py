print("🚀 終極完全體啟動：自動清洗 + 智慧中文簡稱 + 絕不換行表格排版...")
import pandas as pd
import os
import glob
import re
from collections import defaultdict

# 🌟 核心進化：美股與日股中文簡稱庫 (限制 2-4 字，保證手機不換行)
STOCK_NAME_MAP = {
    "NVDA": "輝達", "AAPL": "蘋果", "MSFT": "微軟", "AMZN": "亞馬遜", 
    "GOOGL": "谷歌", "META": "臉書", "TSLA": "特斯拉", "AMD": "超微", 
    "AVGO": "博通", "TXN": "德儀", "QCOM": "高通", "MU": "美光", 
    "INTC": "英特爾", "CRWD": "資安雲", "ASML": "艾司摩爾",
    "6857": "愛德萬", "7011": "三菱重工", "9984": "軟銀"
}

ETF_MAPPING = {
    "00403A": "統一升級50", "00981A": "統一台股增長", "00988A": "統一全球創新",
    "00991A": "復華未來50", "00992A": "群益科技",
    "00405A": "富邦台灣龍耀", "00402A": "安聯美國科技"
}

# (省略重複的 extract_fund_size, find_header_row, smart_read_and_clean 函式，維持原邏輯)
# [請保留您上一次程式中這三個函式的內容]

def generate():
    os.makedirs('dist', exist_ok=True)
    all_files = [f for f in glob.glob(os.path.join('data', "*")) if not os.path.basename(f).startswith('.')]
    if not all_files: return

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

    if not valid_report_dates: return

    with open('templates/index.html', 'r', encoding='utf-8') as f:
        html_template = f.read()

    for target_date in valid_report_dates:
        etf_blocks_html = ""
        for etf_code, dates_files in sorted(etf_history.items()):
            if target_date not in dates_files: continue 
            available_dates = sorted([d for d in dates_files.keys() if d <= target_date], reverse=True)
            if len(available_dates) < 2: continue 
            previous_date = available_dates[1]
            res_today = smart_read_and_clean(dates_files[target_date])
            res_yest = smart_read_and_clean(dates_files[previous_date])
            if res_today[0] is None or res_yest[0] is None: continue

            df_today, size_today = res_today
            top20_items = df_today.sort_values(by=['Weight', 'Qty'], ascending=[False, False]).head(20)
            
            top20_html = ""
            for rank, row in enumerate(top20_items.itertuples(), 1):
                code_str = str(row.Code).replace('.0', '').split()[0] # 清理代號
                # 🌟 智慧簡稱機制：從 STOCK_NAME_MAP 查找，找不到就留空
                name_display = STOCK_NAME_MAP.get(code_str, str(row.Name))
                # 如果是台股(純數字)，優先顯示原名
                if code_str.isdigit(): name_display = str(row.Name)

                top20_html += f'''
                <tr style="border-bottom: 1px solid #e2e8f0; height: 50px;">
                    <td style="padding: 10px 16px; width: 40px; color: #64748b; font-size: 15px; font-weight: bold;">#{rank}</td>
                    <td style="padding: 10px 8px; width: 80px; font-family: monospace; color: #475569; font-size: 16px; font-weight: 600;">{code_str}</td>
                    <td style="padding: 10px 8px; font-weight: 700; color: #1e293b; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px;">{name_display}</td>
                    <td style="padding: 10px 16px; text-align: right; color: #0ea5e9; font-weight: 900; font-size: 17px;">{f"{row.Weight:.2f}%" if row.Weight > 0 else f"{int(row.Qty):,} 股"}</td>
                </tr>
                '''
            
            # (省略 buy_html/sell_html 組裝邏輯，請保持與上一版 Table 風格一致，並將 name_display 套用簡稱邏輯即可)
            # ... [這裡建議您直接把上一版 buy_html/sell_html 迴圈裡的 name_display 換成 STOCK_NAME_MAP.get() 邏輯] ...

        # [其餘 dist/ 檔案產出邏輯維持原樣]

if __name__ == "__main__":
    generate()