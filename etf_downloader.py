import os
import time
import requests
import shutil
import re
import pandas as pd
from datetime import datetime, timedelta  # 🌟 新增 timedelta 來計算回溯日期
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

    # 1. 復華 (00991A 與 00409A) - 🌟 加入自動回溯機制
    fuhwa_etfs = [("00991A", "ETF23"), ("00409A", "ETF26")]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for code, api_code in fuhwa_etfs:
        try:
            print(f"🌐 抓取 {code} (復華)...")
            success = False
            # 往前找最多 5 天的檔案 (避開假日與未更新的時間差)
            for offset in range(5):
                target_date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
                url = f"https://www.fhtrust.com.tw/api/assetsExcel/{api_code}/{target_date}"
                r = requests.get(url, headers=headers, timeout=10)
                
                # 如果狀態碼是 200 且檔案大於 1KB (不是空的錯誤檔)
                if r.status_code == 200 and len(r.content) > 1000:
                    with open(f"data/{code}_{target_date}.xlsx", "wb") as f: 
                        f.write(r.content)
                    print(f"  ✅ {code} 下載成功 (資料日期: {target_date})")
                    success = True
                    break
            
            if not success:
                print(f"  ❌ {code} 失敗: 往前追溯 5 日皆無有效檔案")
        except Exception as e: 
            print(f"  ❌ {code} 失敗: {e}")

    # 2. 安聯 0402A
    print("🌐 抓取 0402A (安聯)...")
    temp_folder = "temp_402"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://etf.allianzgi.com.tw/etf-info/E0003?tab=4")
        time.sleep(10)
        print("  ⚡ 展開安聯網頁所有隱藏持股...")
        
        while True:
            try:
                more_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '顯示更多')]")
                visible_btns = [b for b in more_btns if b.is_displayed()]
                if not visible_btns: break
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", visible_btns[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", visible_btns[0])
                time.sleep(2)
            except: break
        
        tables = driver.find_elements(By.TAG_NAME, "table")
        target_data = []
        for table in tables:
            rows = table.find_elements(By.TAG_NAME, "tr")
            data = []
            for row in rows:
                cols = row.find_elements(By.XPATH, ".//th | .//td")
                cols_text = [c.text.strip() for c in cols]
                if len(cols_text) >= 3 and any(cols_text): data.append(cols_text)
            if data and any('代號' in str(c) or '名稱' in str(c) or '股票' in str(c) for c in data[0]):
                target_data = data
                break
                
        if len(target_data) > 1:
            nav_str, size_str, st_wt_str = "", "", ""
            try:
                page_text_clean = driver.find_element(By.TAG_NAME, "body").text.replace('\n', ' ').replace('\r', ' ')
                
                nav_match = re.search(r'單位淨值.*?(\d+\.\d+)', page_text_clean)
                size_match = re.search(r'資產價值.*?([\d,]{7,})', page_text_clean) 
                wt_match = re.search(r'股票.*?\(([\d\.]+)%\)', page_text_clean)
                
                if nav_match: nav_str = nav_match.group(1).strip()
                if size_match: size_str = size_match.group(1).replace(',', '').strip()
                if wt_match: st_wt_str = wt_match.group(1).strip() + "%"
                
                print(f"  🔍 成功挖出隱藏數據 -> 淨值: {nav_str}, 規模: {size_str}, 股票比例: {st_wt_str}")
            except Exception as e:
                print("  ⚠️ 淨值/規模抓取失敗，但仍將產出持股:", e)

            columns = target_data[0]
            df = pd.DataFrame(target_data[1:], columns=columns)
            df = df[~df.astype(str).apply(lambda x: x.str.contains('顯示更多|收合|合計')).any(axis=1)]
            
            out_data = []
            if size_str: out_data.append(["基金淨資產價值", size_str] + [""] * (len(columns) - 2))
            if nav_str: out_data.append(["基金每單位淨值", nav_str] + [""] * (len(columns) - 2))
            if st_wt_str: out_data.append(["股票", st_wt_str] + [""] * (len(columns) - 2))
            out_data.append(columns)
            out_data.extend(df.values.tolist())
            
            pd.DataFrame(out_data).to_excel(f"data/0402A_{today_str}.xlsx", index=False, header=False)
            print(f"  ✅ 0402A 成功擷取並自動存檔為 data/0402A_{today_str}.xlsx")
        else: print("  ❌ 0402A 失敗: 無法從網頁擷取到持股表格。")
    except Exception as e: print(f"  ❌ 0402A 失敗: {e}")
    finally:
        try: driver.quit()
        except: pass
        try: shutil.rmtree(temp_folder, ignore_errors=True)
        except: pass

    # 3. 富邦 00405A
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

    # 7. 群益
    qunyi_etfs = [("00992A", "500"), ("00997A", "502")]
    for code, pid in qunyi_etfs:
        print(f"🌐 抓取 {code} (群益)...")
        temp_folder = f"temp_{code.lower()}"
        try:
            if not os.path.exists(temp_folder): os.makedirs(temp_folder)
            driver = get_driver(temp_folder)
            driver.get(f"https://www.capitalfund.com.tw/etf/product/detail/{pid}/portfolio")
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
            standardize_file(temp_folder, code, today_str)
        except Exception as e: print(f"  ❌ {code} 失敗: {e}")
        finally:
            try: driver.quit()
            except: pass
            try: shutil.rmtree(temp_folder, ignore_errors=True)
            except: pass

    # 8. 中信 00406A
    print("🌐 抓取 00406A (中信)...")
    temp_folder = "temp_406"
    try:
        if not os.path.exists(temp_folder): os.makedirs(temp_folder)
        driver = get_driver(temp_folder)
        driver.get("https://www.ctbcinvestments.com/Etf/00682450/Combination")
        
        print("  ⚡ 等待中信網頁載入，鎖定下載按鈕...")
        time.sleep(15)
        
        js_script = """
        var tags = ['button', 'a', 'div', 'span'];
        for (var t of tags) {
            var els = document.querySelectorAll(t);
            for (var i = 0; i < els.length; i++) {
                var text = (els[i].textContent || '').replace(/\\s+/g, '').toUpperCase();
                if (text.includes('下載EXCEL') || text === 'EXCEL') {
                    els[i].click();
                    return true;
                }
            }
        }
        return false;
        """
        clicked = driver.execute_script(js_script)
        
        if clicked:
            print("  ⚡ 成功觸發 EXCEL 下載按鈕！")
            standardize_file(temp_folder, "00406A", today_str)
        else:
            print("  ❌ 00406A 失敗: JS 核心腳本也找不到 EXCEL 按鈕。")

    except Exception as e: print(f"  ❌ 00406A 失敗: {e}")
    finally:
        try: driver.quit()
        except: pass
        try: shutil.rmtree(temp_folder, ignore_errors=True)
        except: pass

    print("=== 下載任務全部完成 ===")

if __name__ == "__main__":
    run_download()