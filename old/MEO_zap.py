from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta
import sqlite3
import os
import time
import requests
import sys
import logging
from pathlib import Path

# .envファイルから環境変数を読み込む
load_dotenv()

def setup_logger(username):
    # スクリプトのファイル名を取得（拡張子なし）
    script_name = Path(__file__).stem
    
    # logディレクトリのパスを作成
    log_dir = Path(__file__).parent / 'log'
    log_dir.mkdir(exist_ok=True)
    
    # 現在の日付でログファイル名を生成（ユーザー名を含める）
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = log_dir / f'{script_name}_{username}_{current_date}.log'
    
    # ログフォーマットの設定
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # ファイルハンドラの設定
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # ロガーの設定
    logger = logging.getLogger(f'InstagramScraper_{username}')
    logger.setLevel(logging.INFO)
    
    # 既存のハンドラをクリア（同じユーザーの複数回の実行で重複を防ぐ）
    if logger.hasHandlers():
        logger.handlers.clear()
    
    logger.addHandler(file_handler)
    
    # ログファイルに区切り線と開始メッセージを書き込む
    separator = "=" * 80
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if os.path.exists(log_file):
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{separator}\n")
    
    return logger

def getkey(url):
    """URLからキャッシュキーを抽出"""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('ig_cache_key', [None])[0]

def checkRecord(user_name, cache_key, media_url, logger):
    """データベースでレコードをチェックして保存"""
    DBNAME = os.getenv('DB_NAME')
    TABLENAME = os.getenv('TABLE_NAME')

    conn = None
    try:
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM {TABLENAME} WHERE user_name = ? AND cache_key = ?", (user_name, cache_key))
        result = cursor.fetchone()

        if result is None:
            cursor.execute(f"INSERT INTO {TABLENAME} (user_name, cache_key, media_url) VALUES (?, ?, ?)",  
                           (user_name, cache_key, media_url))
            logger.info(f"新しいレコードを登録しました: user_name={user_name}, cache_key={cache_key}")
            conn.commit()
            return True
        else:
            logger.info(f"レコードが既に存在します: user_name={user_name}, cache_key={cache_key}")
            return False

    except sqlite3.Error as e:
        error_msg = f"データベースエラーが発生しました: {e}"
        logger.error(error_msg)
        print(error_msg)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def setup_chrome_with_profile():
    """Chromeドライバーの設定"""
    chrome_options = Options()
    
    # .envから設定を読み込む
    user_data_dir = os.getenv('CHROME_PROFILE_PATH')
    profile_name = os.getenv('PROFILE_NAME', 'Default')
    
    # オプションを設定
    chrome_options.add_argument(f'user-data-dir={user_data_dir}')
    chrome_options.add_argument(f'--profile-directory={profile_name}')
    
    # その他の必要なオプション
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--headless")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_experimental_option("detach", False)
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-extensions')
    
    # プリファレンス設定
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        error_msg = f"Chromeドライバーの設定でエラーが発生しました: {e}"
        print(error_msg)
        print("注意: Chromeを完全に終了してから実行してください")
        return None

def main():
    # コマンドライン引数の処理
    if len(sys.argv) < 3:
        print("必要な引数が不足しています: USERNAME と ZAP が必要です")
        return

    USERNAME = sys.argv[1]
    ZAP = sys.argv[2]

    logger = setup_logger(USERNAME)
    logger.info("処理開始")
    logger.info(f"対象ユーザー: {USERNAME}")

    driver = setup_chrome_with_profile()
    if not driver:
        logger.error("Chromeドライバーの初期化に失敗しました")
        return
    
    try:
        # Instagramのプロフィールページにアクセス
        logger.info(f"{USERNAME} のプロフィールページにアクセスします")
        driver.get(f'https://www.instagram.com/{USERNAME}/')
        time.sleep(3)

        # プロフィール写真をクリック
        try:
            xpath = f"//img[contains(@alt, '{USERNAME}のプロフィール写真')]"
            profile_image = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            profile_image.click()
            logger.info("プロフィール写真のクリックに成功しました")
        except Exception as e:
            error_msg = f"{USERNAME}のプロフィール画像のクリックに失敗しました: {e}"
            logger.error(error_msg)
            print(error_msg)
            driver.quit()
            return

        # 画像要素の取得
        target_classes = ["xl1xv1r", "x5yr21d", "xmz0i5r", "x193iq5w", "xh8yej3"]
        class_condition = " and ".join([f"contains(@class, '{cls}')" for cls in target_classes])
        xpath = f"//img[{class_condition} and contains(@alt, 'Photo by')]"
        
        try:
            video_check = driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'x10l6tqk')][@data-visualcompletion='ignore']"
            )
        
            if video_check:
                logger.info(f"{USERNAME}: 動画投稿のため、スキップします")
                return
            
            image_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            
            image_url = image_element.get_attribute('src')
            logger.info("画像URLの取得に成功しました")
            
            if image_url:
                cache_key = getkey(image_url)
                result = checkRecord(USERNAME, cache_key, image_url, logger)

                # Zapier連携
                if result:
                    try:
                        url = f"https://hooks.zapier.com/hooks/catch/{ZAP}/"
                        data = {'MediaURL': image_url}
                        response = requests.post(url, json=data)
                        logger.info(f"Zapier連携が成功しました: {response.status_code}")
                    except Exception as e:
                        error_msg = f"Zapier連携でエラーが発生しました: {e}"
                        logger.error(error_msg)
                        print(error_msg)

        except Exception as e:
            error_msg = f"画像の取得に失敗しました: {e}"
            logger.error(error_msg)
            print(error_msg)
            driver.quit()
            return
        
    except Exception as e:
        error_msg = f"実行中にエラーが発生しました: {e}"
        logger.error(error_msg)
        print(error_msg)
        driver.quit()
        return
        
    finally:
        driver.quit()
        logger.info("処理終了")

if __name__ == "__main__":
    main()