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
    print(f"  ⏳ 正在雷達偵測檔案下載狀態...")
    # 🌟 升級版智慧等待：最多等 45 秒，每秒巡邏一次，一下載完立刻收網
    for _ in range(45):
        files = os.listdir(source_folder)
        # 過濾掉尚未下載完成的暫存檔與系統隱藏檔
        valid_files = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp') and not f.startswith('.')]
        
        if valid_files and not any(f.endswith('.crdownload') for f in files):
            latest_file = max([os.path.join(source_folder, f) for f in valid_files], key=os.path.getctime)
            ext = os.path.splitext(latest_file)[1]
            new_name = f"{etf_code}_{today_str}{ext}"
            shutil.move(latest_file, os.path.join("data", new_name))
            print(f"  ✅ 成功捕獲並歸檔至 data/: {new_name}")
            return
            
        time.sleep(1)
        
    raise Exception("等候 45 秒仍未見檔案，可能是按鈕點擊無效或資料尚未生成。")

def get_driver(download_path):
    abs_download_path = os.path.abspath(download_path)
    os.makedirs(abs_download_path, exist_ok=True)
    
    chrome_options = Options()
    prefs = {
        "download.default_directory": abs_download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
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
    
    try:
        driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': abs_download_path,
            'eventsEnabled': True
        })
    except: pass
    
    return driver

def run_download():
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"=== 開始執行下載任務: {today_str} ===")

    # 1. 復華
    try:
        print("🌐 抓取 00991A...")
        url = f"https://www.fhtrust.com.tw/api/assetsExcel/ETF23/{today_str}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(f"data/00991A_{today_str}.xlsx", "wb") as f: f.write(r.content)
            print("  ✅ 00991A 下載成功")
    except Exception as e: print(f"  ❌ 00991A 失敗: {e}")

    # 2, 4, 5. 統一
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
            standardize_file(temp_folder, code, today_str) # 統一也改用智慧雷達偵測
        except Exception as e: print(f"  ❌ {code} 失敗: {e}")
        finally: 
            try: driver.quit()
            except: pass
            try: shutil.rmtree(temp_folder, ignore_errors=True)
            except: pass

    # 3. 群益
    print("🌐 抓取 00992A...")
    temp_folder = "temp_992"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://www.capitalfund.com.tw/etf/product/detail/500/portfolio")
        
        # 🌟 破案關鍵 1：強迫等待 8 秒！讓群益網站的資料庫徹底把按鈕功能綁定好
        print("  ⏳ 正在等待群益網頁底層資料庫連結...")
        time.sleep(8) 
        
        # 🌟 破案關鍵 2：找出畫面上「所有」下載按鈕，並避開隱藏的陷阱
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), '下載資料') or contains(text(), '匯出')]")
        
        clicked = False
        for btn in btns:
            if btn.is_displayed():
                print("  ⚡ 鎖定可見的下載按鈕，準備點擊...")
                # 滑動螢幕對準它，避免被其他浮動視窗擋住
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(1)
                try:
                    btn.click() # 正規點擊
                    clicked = True
                except:
                    driver.execute_script("arguments[0].click();", btn) # 強制點擊
                    clicked = True
                break
                
        if not clicked and btns:
            print("  ⚠️ 找不到可見按鈕，對首個隱藏按鈕發射強制點擊！")
            driver.execute_script("arguments[0].click();", btns[0])

        # 使用智慧雷達偵測 992A 的檔案
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