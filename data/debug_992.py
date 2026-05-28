import pandas as pd
import os

def debug_read(filepath):
    print(f"正在分析檔案: {filepath}")
    xl = pd.ExcelFile(filepath)
    print(f"檔案包含分頁: {xl.sheet_names}")
    for sheet in xl.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet, header=None)
        print(f"\n--- 分頁 {sheet} 前 10 行內容 ---")
        print(df.head(10))

# 請確認這個檔案路徑是您 data/ 資料夾內那個 992A 的正確檔名
debug_read('data/00992A_20260528.xlsx')