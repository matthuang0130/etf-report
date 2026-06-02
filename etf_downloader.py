import os
import time
import requests
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 確保 data 資料夾存在
if not os.path.exists("data"): os.makedirs("data")

def standardize_file(source_folder, etf_code, today_str):
    # 🌟 確保沒有尚未下載完成的暫存檔 (.crdownload)
    for _ in range(15):
        files = os.listdir(source_folder)
        if any(f.endswith('.crdownload') or f.endswith('.tmp') for f in files):
            time.sleep(2)
        else:
            break
            
    files = [os.path.join(source_folder, f) for f in os.listdir(source_folder) if not f.endswith('.crdownload') and not f.endswith('.tmp')]
    
    # 🌟 加上這道防線：如果資料夾沒檔案，必須大聲報錯！
    if not files: 
        raise Exception("點擊了下載，但被雲端瀏覽器安全性阻擋，檔案未成功存入")
        
    latest_file = max(files, key=os.path.getctime)
    ext = os.path.splitext(latest_file)[1]
    new_name = f"{etf_code}_{today_str}{ext}"
    shutil.move(latest_file, os.path.join("data", new_name))
    print(f"  ✅ 已歸檔至 data/: {new_name}")

def get_driver(download_path):
    abs_download_path = os.path.abspath(download_path)
    chrome_options = Options()
    prefs = {
        "download.default_directory": abs_download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False # 避免雲端防護擋下 Excel
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # 🌟 2026 終極隱形斗篷設定
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-blink-features=AutomationControlled") 
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # 🌟 針對 Linux 雲端環境，強制開啟下載權限 (VIP 通行證)
    driver.execute_cdp_cmd('Page.setDownloadBehavior', {
        'behavior': 'allow',
        'downloadPath': abs_download_path
    })
    
    return driver

def run_download():
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"=== 開始執行下載任務: {today_str} ===")

    # 1. 復華 (復華沒問題，不改)
    try:
        print("🌐 抓取 00991A...")
        url = f"https://www.fhtrust.com.tw/api/assetsExcel/ETF23/{today_str}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(f"data/00991A_{today_str}.xlsx", "wb") as f: f.write(r.content)
            print("  ✅ 00991A 下載成功")
    except Exception as e: print(f"  ❌ 00991A 失敗: {e}")

    # 2, 4, 5. 統一 (使用迴圈處理，單個失敗不影響其他)
    etfs = [("00981A", "49YTW"), ("00403A", "63YTW"), ("00988A", "61YTW")]
    for code, fund_code in etfs:
        print(f"🌐 抓取 {code}...")
        temp_folder = f"temp_{code}"
        try:
            if not os.path.exists(temp_folder): os.makedirs(temp_folder)
            driver = get_driver(temp_folder)
            driver.get(f'https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode={fund_code}')
            wait = WebDriverWait(driver, 20)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '基金投資組合')]"))).click()
            time.sleep(2)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., '匯出')]"))).click()
            time.sleep(10)
            standardize_file(temp_folder, code, today_str)
        except Exception as e: print(f"  ❌ {code} 失敗: {e}")
        finally: 
            try: driver.quit()
            except: pass
            try: shutil.rmtree(temp_folder, ignore_errors=True)
            except: pass

    # 3. 群益 (群益獨立處理)
    print("🌐 抓取 00992A...")
    temp_folder = "temp_992"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://www.capitalfund.com.tw/etf/product/detail/500/portfolio")
        wait = WebDriverWait(driver, 30)
        btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'下載資料')]")))
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(20)
        standardize_file(temp_folder, "00992A", today_str)
    except Exception as e: print(f"  ❌ 00992A 失敗: {e}")
    finally:
        try: driver.quit()
        except: pass
        try: shutil.rmtree(temp_folder, ignore_errors=True)
        except: pass

    print("=== 下載任務全部完成，準備自動產生報表 ===")

if __name__ == "__main__":
    run_download()