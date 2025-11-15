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
import sys
import logging
from pathlib import Path
import requests
import json
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from MEO import download_media, extract_request_urls, get_complete_media_url, getkey_blob, checkRecord, getkey
import io

# 標準出力のエンコーディングをUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

def setup_logger(username):
    # スクリプトのファイル名を取得（拡張子なし）
    script_name = Path(__file__).stem
    

    # 現在の日付を取得
    current_date = datetime.now().strftime('%Y%m%d')
    
    # logディレクトリと日付ディレクトリのパスを作成
    log_dir = Path(__file__).parent / 'log' / current_date
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 現在の日付でログファイル名を生成（ユーザー名を含める）
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
    #headless
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


    # パフォーマンスログの設定
    chrome_options.set_capability(
        "goog:loggingPrefs", 
        {"performance": "ALL"}
    )
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        #driver = webdriver.Chrome(service=service, options=chrome_options, desired_capabilities=caps)

        return driver
    except Exception as e:
        error_msg = f"Chromeドライバーの設定でエラーが発生しました: {e}"
        print(error_msg)
        print("注意: Chromeを完全に終了してから実行してください")
        return None
    
import psutil
import random
def get_chrome_driver_v2(logger):
    """Chromeドライバーの設定（並列実行対応）"""
    load_dotenv()
    
    # 使用中のデバッグポートを確認
    used_ports = set()
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.cmdline()
            for cmd in cmdline:
                if '--remote-debugging-port=' in cmd:
                    try:
                        port = int(cmd.split('=')[1])
                        used_ports.add(port)
                    except:
                        continue
        except:
            continue
    
    # 利用可能なポートを見つける
    port = 9222
    while port in used_ports:
        port += 1
    logger.info(f"Selected port for this instance: {port}")

    chrome_options = Options()
   
    # .envから設定を読み込む
    user_data_dir = os.getenv('CHROME_PROFILE_PATH')
    #profile_name = os.getenv('PROFILE_NAME', 'Default')

    profile_name = random.choice([
        os.getenv('PROFILE_NAME'),
        os.getenv('PROFILE_NAME_2'),
        os.getenv('PROFILE_NAME_3'),
        os.getenv('PROFILE_NAME_5')
    ])
    logger.info(f"選択されたプロファイル: {profile_name}")

   
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
    chrome_options.add_argument(f'--remote-debugging-port={port}')  # 動的なポート割り当て
    chrome_options.add_experimental_option("detach", False)
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument(f'--window-position={(port - 9222) * 100},0')  # ウィンドウ位置を分離
   
    # プリファレンス設定
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # パフォーマンスログの設定
    chrome_options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )
   
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        error_msg = f"Chromeドライバーの設定でエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error("注意: Chromeを完全に終了してから実行してください")
        return None

def wait_for_lock(logger, max_wait_minutes):
    script_dir = Path(__file__).parent
    lock_dir = script_dir / 'lock'
    lock_dir.mkdir(exist_ok=True)
    lock_file = lock_dir / 'glink.lock'
    
    wait_start = time.time()
    logger.info("ロックファイルをチェックします")
    time.sleep(1.5)
    
    while lock_file.exists():
        try:
            if (time.time() - lock_file.stat().st_mtime) > 3600:
                lock_file.unlink()
                logger.warning("古いロックファイルを削除しました")
                break
        except Exception as e:
            logger.error(f"ロックファイルの確認中にエラー: {e}")
        
        if (time.time() - wait_start) > (max_wait_minutes * 60):
            logger.error(f"最大待機時間（{max_wait_minutes}分）を超過しました")
            sys.exit(1)
        
        logger.info("他のタスクが実行中です。待機します...")
        time.sleep(5)
    
    try:
        lock_file.touch()
        logger.info("ロックファイルを作成しました")
    except Exception as e:
        logger.error(f"ロックファイル作成時のエラー: {e}")
        sys.exit(1)
    
    return lock_file



def main():
    # コマンドライン引数の処理
    if len(sys.argv) < 3:
        print("必要な引数が不足しています: USERNAME, process_idが必要です")
        return 1

    USERNAME = sys.argv[1]
    process_id = sys.argv[2]
    
    logger = setup_logger(USERNAME)
    logger.info(f"処理開始 PROCESSID:{process_id}")
    logger.info(f"対象ユーザー: {USERNAME}")
    
    lock_file = None
    try:

        ##### lock処理 #####
        lock_file = wait_for_lock(logger, max_wait_minutes=30)
        logger.info("処理を開始します")


        

        #driver = setup_chrome_with_profile()
        driver = get_chrome_driver_v2(logger)


        if not driver:
            logger.error("Chromeドライバーの初期化に失敗しました")
            return 1
        
        ########## Instagramのプロフィールページにアクセス ##########
        try:
            logger.info(f"{USERNAME} のプロフィールページにアクセスします")
            driver.get(f'https://www.instagram.com/{USERNAME}/')

            time.sleep(5)

        except Exception as e:
            error_msg = f"実行中にエラーが発生しました: {e}"
            logger.error(error_msg)
            print(error_msg)
            driver.quit()
            return 1
        

        ########## 最新投稿読み込み ##########
        # Facebookのエラーページをチェック
        facebook_error_elements = driver.find_elements(
            By.XPATH,
            "//h1[contains(text(), 'Sorry, something went wrong')] | //div[@class='core']//p[contains(text(), 'working on getting this fixed')]"
        )
        if facebook_error_elements and facebook_error_elements[0].is_displayed():
            logger.error("アカウントの自動化が検出された可能性があります")
            return 3


        # ページが利用できない場合のメッセージをチェック
        unavailable_elements = driver.find_elements(
            By.XPATH, 
            "//span[contains(text(), 'このページはご利用いただけません')] | //span[contains(text(), 'リンクに問題があるか、ページが削除された可能性があります')]"
        )
        if unavailable_elements and unavailable_elements[0].is_displayed():
            logger.error("ユーザネームの変更、またはブロックされた可能性があります")
            return 1

        # エラーページのチェック
        error_elements = driver.find_elements(
            By.XPATH, 
            "//span[contains(text(), 'エラーが発生しました')] | //span[contains(text(), '問題が発生したため、ページを読み込めませんでした')]"
        )
        if error_elements and error_elements[0].is_displayed():
            logger.info("アカウントがロックされました")
            return 3  # または必要な戻り値

        # 投稿がない場合のメッセージの存在チェック
        no_posts_elements = driver.find_elements(By.XPATH, "//span[contains(text(), '投稿はまだありません')]")
        if no_posts_elements and no_posts_elements[0].is_displayed():
            logger.info("投稿はまだありません")
            return 1


        try:
            logger.info("最新投稿を読み込みます")

            time.sleep(5)

            wait = WebDriverWait(driver, 20)
            containers = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div._ac7v.x1f01sob")
            ))
            
            # すべてのコンテナから投稿リンクを収集
            latest_post_url = None
            for container in containers:
                post_links = container.find_elements(By.CSS_SELECTOR, "a[role='link']._a6hd")
                
                for link in post_links:
                    # ピン留めアイコンの有無を確認
                    #pinned_icon = link.find_elements(By.CSS_SELECTOR, "svg[aria-label='固定された投稿のアイコン']")

                    pinned_icon = link.find_elements(By.CSS_SELECTOR, "svg[aria-label='ピン留めされた投稿のアイコン']")



                    if not pinned_icon:
                        latest_post_url = link.get_attribute('href')
                        # 最初に見つかった非固定投稿が最新のものなので、即座にループを抜ける
                        break
                
                if latest_post_url:
                    break
            
            if latest_post_url:
                print(f"最新投稿のURL: {latest_post_url}")
                # 投稿ページに直接アクセス
                driver.get(latest_post_url)
                time.sleep(2)
                print("最新投稿ページにアクセスしました")
                logger.info("最新投稿ページにアクセスしました")
            else:
                print("最新の非固定投稿が見つかりませんでした")
                logger.info("最新の非固定投稿が見つかりませんでした")
                
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            logger.error(f"最新投稿読み込みでエラーが発生しました: {str(e)}")
            logger.error(f"エラーの種類: {type(e).__name__}")


            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # エラー情報保存用のディレクトリ
                error_dir = Path(__file__).parent / 'error_shots'
                error_dir.mkdir(parents=True, exist_ok=True)
                
                # スクリーンショット保存
                screenshot_path = error_dir / f'error_{timestamp}.png'
                driver.save_screenshot(str(screenshot_path))
                
                # HTML保存
                html_path = error_dir / f'error_{timestamp}.html'
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)

                logger.info(f"エラー時の内容を保存しました")

            except Exception as save_error:
                logger.error(f"エラー情報の保存に失敗: {str(save_error)}")





        ########## 最新投稿の種別確認 ##########
        post_date = ""
        media_urls = []
        description = ""
        try:
            # 要素が読み込まれるまで待機
            wait = WebDriverWait(driver, 20)

            try:
        
                
                # time要素を取得
                wait = WebDriverWait(driver, 10)
                time_element = wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
                
                # datetime属性から日時を取得
                date_str = time_element.get_attribute('datetime')
                if date_str is None:
                    raise ValueError("datetime属性が見つかりません")
                    
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                jst = timezone(timedelta(hours=+9), 'JST')
                date_jst = date.astimezone(jst)  # JSTに変換
                post_date = date_jst.strftime('%Y%m%d')     

                logger.info(f"date:{date_jst}")
                logger.info(f"post_date:{post_date}")
                print(f"post_date:{post_date}") 

                start_date = os.getenv(f'{USERNAME}_start')
                print(f"start_date:{start_date}")
                # 日付を比較
                if post_date < start_date:
                    print(f"投稿日付 {post_date} は開始日 {start_date} より前のため、処理を終了します")
                    logger.info(f"投稿日付 {post_date} は開始日 {start_date} より前のため、処理を終了します")
                    driver.quit()
                    return 1


            except Exception as e:
                print(f"投稿日時取得失敗: {str(e)}")
                return 1


            ########## 動画 ##########
            # 複数動画は一旦サーバー負荷考慮で未対応にする
            try:
                video_element = driver.find_element(By.CSS_SELECTOR, "video.x1lliihq")
                #media_url = video_element.get_attribute('src')
                media_urls.append(video_element.get_attribute('src'))
                media_type = 'video'

            except NoSuchElementException:
                ########## 複数画像_カルーセル ##########
                
                indicators = driver.find_elements(By.CSS_SELECTOR, "div._acnb")
                total_images = len(indicators)

                if total_images > 1:
                    # 現在のURLから基本URLを取得
                    base_url = driver.current_url
                    if "/?img_index=" in base_url:
                        base_url = base_url.split("/?img_index=")[0]
                    
                    # 最初の画像を取得（初回表示）
                    img_element = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div._aagv img")
                    ))
                    media_url = img_element.get_attribute('src')
                    if media_url:
                        media_urls.append(media_url) 
                        
                    # 2枚目以降は個別にアクセス
                    for index in range(2, total_images + 1):
                        carousel_url = f"{base_url}/?img_index={index}"
                        driver.get(carousel_url)
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._aagv")))
                        time.sleep(1)
                        
                        # 2枚目のimg要素を取得
                        img_elements = driver.find_elements(By.CSS_SELECTOR, "div._aagv img")
                        if len(img_elements) >= 2:
                            media_url = img_elements[1].get_attribute('src')  # 2番目の要素を取得
                            if media_url and media_url not in media_urls:
                                media_urls.append(media_url)
                            
                    media_type = 'image_carousel'

                ########## 単一画像 ##########
                else:
                    img_element = wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div._aagv img")
                    ))
                    media_url = img_element.get_attribute('src')
                    media_urls.append(media_url)
                    media_type = 'image'



            print(f"メディアタイプ: {media_type}")
            print("メディアURL:")
            for i, url in enumerate(media_urls, 1):
                print(f"{i}枚目: {url}")
                logger.info(f"{i}枚目: {url}")
            
            ########## 説明文取得 ##########
            try:
                """
                description = driver.find_element(
                    By.CSS_SELECTOR,
                    "div._a9zs h1._ap3a._aaco._aacu._aacx._aad7._aade"
                ).text
                """
                
                description = wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        'h1._ap3a._aaco._aacu._aacx._aad7._aade'
                    ))
                ).text
                #print(f"説明文: {description}")
                logger.info(f"説明文: {description}")



                # ディレクトリパスを構築
                description_dir = os.path.join('media', USERNAME, 'description')
                if not os.path.exists(description_dir):
                    os.makedirs(description_dir)

                # 一時ファイルのパス（プロセスIDを含む）
                temp_file_path = os.path.join(description_dir, f'{process_id}')

                # データを一時ファイルに書き込み
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(description)



            except:
                print("説明文なし")
                description = None
        
        except Exception as e:
            print(f"最新投稿の要素読み込みでエラーが発生しました: {str(e)}")

        # メディア取得
        try:
            flg = False
            for media_url in media_urls:
                # URLがblobで始まる場合の特別処理
                if media_url == media_url and media_url.startswith('blob:'):
                    print("blobで始まるURLを検出しました")
                    time.sleep(1)
                    # ネットワーク取得
                    netlog = driver.get_log("performance")
                    # url(部分的)取得
                    urls = extract_request_urls(netlog)
                    # url結合
                    complete_url = get_complete_media_url(urls)
                    print(complete_url)
                    logger.info(f"生成URL:{complete_url}")
                    
                    cache_key = getkey_blob(complete_url)
                    if cache_key is None:
                        logger.error("Keyの取得に失敗しました")
                        driver.quit()
                        return 1
                        
                    result_blob = checkRecord(USERNAME, cache_key, complete_url, logger)
                    if result_blob:
                        # 動画DL
                        download_media(logger, complete_url, USERNAME, "mp4")
                        flg = True
                    else:
                        logger.info("このレコードは存在します")
                        #driver.quit()
                        #return 1
                        continue
                
                else:
                    logger.info("画像URLを取得しました")
                    cache_key = getkey(media_url)
                    result = checkRecord(USERNAME, cache_key, media_url, logger)

                    if result:
                        logger.info("メディアを取得します")
                        download_media(logger, media_url, USERNAME, "jpg")
                        flg = True
                    else:
                        logger.info("このレコードは存在します")
                        #driver.quit()
                        #return 1
                        continue
            
            if(not flg):
                logger.info("全件レコードが存在します")
                driver.quit()
                return 1
            else:
                print(f"説明文:{description}")
                logger.info(f"説明文:{description}")
                
        except Exception as e:
            print(f"メディア取得でエラーが発生しました: {str(e)}")
        
        driver.quit()
        logger.info("処理終了")

        return 0
    
    finally:
        driver.quit()
        # このブロックは必ず実行される
        if lock_file and lock_file.exists():
            try:
                lock_file.unlink()
                logger.info("ロックファイルを削除しました")
            except Exception as e:
                logger.error(f"ロックファイル削除時のエラー: {e}")

if __name__ == "__main__":
    result = main()

    #print(result)
    sys.exit(result)