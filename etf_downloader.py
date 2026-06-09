import os
import time
import requests
import shutil
import pandas as pd
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
    for _ in range(45):
        try:
            files = os.listdir(source_folder)
            valid_files = [f for f in files if f.endswith(('.xlsx', '.xls', '.csv'))]
            
            if valid_files and not any(f.endswith('.crdownload') or f.endswith('.tmp') for f in files):
                latest_file = max([os.path.join(source_folder, f) for f in valid_files], key=os.path.getctime)
                new_name = f"{etf_code}_{today_str}{os.path.splitext(latest_file)[1]}"
                shutil.move(latest_file, os.path.join("data", new_name))
                print(f"  ✅ 成功捕獲並歸檔至 data/: {new_name}")
                return
        except Exception:
            pass
        time.sleep(1)
    raise Exception("等候 45 秒仍未見有效的 Excel/CSV 檔案。")

def get_driver(download_path):
    abs_download_path = os.path.abspath(download_path)
    os.makedirs(abs_download_path, exist_ok=True)
    chrome_options = Options()
    prefs = {"download.default_directory": abs_download_path, "download.prompt_for_download": False}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': abs_download_path})
    return driver

def run_download():
    today_str = datetime.now().strftime("%Y%m%d")
    print(f"=== 開始執行下載任務: {today_str} ===")

    # 1. 復華 00991A
    try:
        print("🌐 抓取 00991A...")
        r = requests.get(f"https://www.fhtrust.com.tw/api/assetsExcel/ETF23/{today_str}", timeout=10)
        if r.status_code == 200:
            with open(f"data/00991A_{today_str}.xlsx", "wb") as f: f.write(r.content)
            print("  ✅ 00991A 下載成功")
    except Exception as e: print(f"  ❌ 00991A 失敗: {e}")

    # 2. 安聯 0402A (無下載按鈕，直接暴力擷取網頁表格)
    print("🌐 抓取 0402A (安聯)...")
    temp_folder = "temp_402"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://etf.allianzgi.com.tw/etf-info/E0003?tab=4")
        time.sleep(10) # 讓安聯網頁充分載入
        
        print("  ⚡ 展開安聯網頁所有隱藏持股...")
        while True:
            try:
                more_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '顯示更多')]")
                visible_btns = [b for b in more_btns if b.is_displayed()]
                if not visible_btns:
                    break
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", visible_btns[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", visible_btns[0])
                time.sleep(2)
            except:
                break
                
        print("  ⚡ 直接擷取安聯網頁表格資料...")
        tables = driver.find_elements(By.TAG_NAME, "table")
        target_data = []
        for table in tables:
            rows = table.find_elements(By.TAG_NAME, "tr")
            data = []
            for row in rows:
                cols = row.find_elements(By.XPATH, ".//th | .//td")
                cols_text = [c.text.strip() for c in cols]
                if len(cols_text) >= 3 and any(cols_text):
                    data.append(cols_text)
            
            # 確保這是持股表格
            if data and any('代號' in str(c) or '名稱' in str(c) or '股票' in str(c) for c in data[0]):
                target_data = data
                break
                
        if len(target_data) > 1:
            columns = target_data[0]
            df = pd.DataFrame(target_data[1:], columns=columns)
            
            # 過濾掉包含「顯示更多」、「收合」或「合計」的雜訊列
            df = df[~df.astype(str).apply(lambda x: x.str.contains('顯示更多|收合|合計')).any(axis=1)]
            
            df.to_excel(f"data/0402A_{today_str}.xlsx", index=False)
            print(f"  ✅ 0402A 成功擷取並自動存檔為 data/0402A_{today_str}.xlsx")
        else:
            print("  ❌ 0402A 失敗: 無法從網頁擷取到持股表格。")
    except Exception as e: print(f"  ❌ 0402A 失敗: {e}")
    finally:
        try: driver.quit()
        except: pass
        try: shutil.rmtree(temp_folder, ignore_errors=True)
        except: pass

    # 3. 富邦 00405A (精準點擊 ID)
    print("🌐 抓取 00405A...")
    temp_folder = "temp_405"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://websys.fsit.com.tw/FubonETF/Fund/Assets.aspx?stkId=00405A")
        time.sleep(5)
        btn = driver.find_element(By.ID, "mainContent_subMainContent_btnDownload")
        driver.execute_script("arguments[0].click();", btn)
        standardize_file(temp_folder, "00405A", today_str)
    except Exception as e: print(f"  ❌ 00405A 失敗: {e}")
    finally:
        try: driver.quit()
        except: pass
        try: shutil.rmtree(temp_folder, ignore_errors=True)
        except: pass

    # 4, 5, 6. 統一
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
            standardize_file(temp_folder, code, today_str) 
        except Exception as e: print(f"  ❌ {code} 失敗: {e}")
        finally: 
            try: driver.quit()
            except: pass
            try: shutil.rmtree(temp_folder, ignore_errors=True)
            except: pass

    # 7. 群益 00992A
    print("🌐 抓取 00992A...")
    temp_folder = "temp_992"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://www.capitalfund.com.tw/etf/product/detail/500/portfolio")
        time.sleep(8) 
        btns = driver.find_elements(By.XPATH, "//*[contains(text(), '下載資料') or contains(text(), '匯出')]")
        clicked = False
        for btn in btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                break
        if not clicked and btns:
            driver.execute_script("arguments[0].click();", btns[0])
        standardize_file(temp_folder, "00992A", today_str)
    except Exception as e: print(f"  ❌ 00992A 失敗: {e}")
    finally:
        try: driver.quit()
        except: pass
        try: shutil.rmtree(temp_folder, ignore_errors=True)
        except: pass

    print("=== 下載任務全部完成 ===")

if __name__ == "__main__":
    run_download()