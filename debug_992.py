import pandas as pd
import glob

print("🔍 啟動 992A 透視鏡...")

# 自動去 data 資料夾找 992A 的檔案，不用手動改日期
files = glob.glob("data/*992A*.xlsx")

if not files:
    print("❌ 找不到 992A 的檔案，請確認 data/ 資料夾內有檔案。")
else:
    # 抓第一份 992A 檔案來透視
    filepath = files[0]
    print(f"✅ 成功鎖定檔案: {filepath}")
    
    try:
        xl = pd.ExcelFile(filepath)
        print(f"📑 檔案內含分頁: {xl.sheet_names}")
        
        # 把每個分頁的前 15 行印出來，讓我們看清楚表頭在哪
        for sheet in xl.sheet_names:
            print(f"\n{'='*40}")
            print(f"📊 分頁: {sheet} (前 15 行)")
            print(f"{'='*40}")
            df = pd.read_excel(filepath, sheet_name=sheet, header=None)
            print(df.head(15))
            
    except Exception as e:
        print(f"❌ 讀取發生錯誤: {e}")