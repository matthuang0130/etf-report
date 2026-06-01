print("🚀 終極完全體啟動：自動清洗 + 自動比對差額 + 網頁產出...")
import pandas as pd
import os
import glob
import re
from collections import defaultdict

ETF_MAPPING = {
    "00403A": "統一升級50", "00981A": "統一台股增長", "00988A": "統一全球創新",
    "00991A": "復華未來50", "00992A": "群益科技"
}

def find_header_row(df):
    # 🌟 升級：把掃描深度拉到 50 行，對付統一的多行廢話
    for i in range(min(50, len(df))): 
        row_str = "".join(str(x) for x in df.iloc[i].values).lower()
        if ('代' in row_str or 'code' in row_str) and ('股' in row_str or '權重' in row_str or 'qty' in row_str):
            return i
    return -1

def smart_read_and_clean(filepath):
    # 🌟 絕對防禦：如果是 Excel 產生的隱藏鎖定檔，直接無視，不要去讀它
    if os.path.basename(filepath).startswith('~$'):
        return None

    try:
        if filepath.endswith('.csv'):
            try: df_raw = pd.read_csv(filepath, encoding='utf-8', header=None)
            except: df_raw = pd.read_csv(filepath, encoding='big5', header=None)
            sheets = {'Sheet1': df_raw}
        else:
            # 使用 sheet_name=None 確保能讀取到所有分頁 (如 992A)
            sheets = pd.read_excel(filepath, sheet_name=None, header=None)

        all_clean_data = []
        for sheet_name, df in sheets.items():
            header_idx = find_header_row(df)
            if header_idx == -1: continue # 找不到就跳過該分頁

            df.columns = df.iloc[header_idx].astype(str)
            df = df.iloc[header_idx+1:].reset_index(drop=True)

            col_code, col_name, col_qty = None, None, None
            for c in df.columns:
                c_str = str(c).lower().strip()
                if not col_code and ('代' in c_str or 'code' in c_str): 
                    col_code = c
                elif not col_name and ('名' in c_str or 'name' in c_str): 
                    col_name = c
                # 🌟 破案關鍵：找數量時，絕對避開「權重」與「%」
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
            # 確保所有分頁數據正確加總，並且把 Name 綁在一起不遺失
            combined = pd.concat(all_clean_data, ignore_index=True)
            return combined.groupby(['Code', 'Name'], as_index=False)['Qty'].sum()
        return None
    except Exception as e:
        print(f"❌ 讀取失敗 {os.path.basename(filepath)}: {e}")
        return None

def