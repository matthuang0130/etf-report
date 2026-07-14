import requests
import os
import urllib3
from datetime import datetime

# 🌟 徹底無視 SSL 憑證檢查，這能繞過您電腦的驗證報錯
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_ctbc_robust():
    today_str = datetime.now().strftime("%Y%m%d")
    url = "https://www.ctbcinvestments.com/api/etf/export/00682450/Combination?type=excel"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Referer": "https://www.ctbcinvestments.com/Etf/00682450/Combination"
    }

    print("🌐 正在執行終極下載任務...")
    try:
        # verify=False 是繞過 SSL 錯誤的關鍵
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            if not os.path.exists("data"): os.makedirs("data")
            filepath = os.path.join("data", f"00406A_{today_str}.xlsx")
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"✅ 成功下載並歸檔: {filepath}")
        else:
            print(f"❌ 下載失敗，伺服器回應: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    download_ctbc_robust()