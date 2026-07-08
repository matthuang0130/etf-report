import pandas as pd
import datetime
import os
import requests
import urllib3

# 🌟 關閉煩人的 SSL 不安全連線警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_ctbc_00406A():
    url = "https://www.ctbcinvestments.com/Etf/00682450/Combination"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("⏳ 正在連線至中國信託投信，下載 00406A (台灣收益成長) 投資組合...")
    try:
        # 🌟 核心修正：加上 verify=False，強行繞過 SSL 憑證阻擋
        response = requests.get(url, headers=headers, verify=False)
        response.encoding = 'utf-8'
        
        # 使用 pandas 解析網頁中的表格
        dfs = pd.read_html(response.text)
        
        if dfs:
            df = dfs[0] # 假設第一個表格為持股明細
            
            # 建立 data 資料夾與設定檔名 (例如: 00406A_20260707.csv)
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            os.makedirs("data", exist_ok=True)
            filepath = os.path.join("data", f"00406A_{today_str}.csv")
            
            # 儲存為 CSV，使用 utf-8-sig 確保 Excel 開啟不會亂碼
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"✅ 成功下載！檔案已儲存至: {filepath}")
        else:
            print("❌ 找不到表格資料，可能網頁有阻擋或改為動態載入。")
            
    except Exception as e:
        print(f"❌ 發生錯誤，下載失敗: {e}")

if __name__ == "__main__":
    download_ctbc_00406A()