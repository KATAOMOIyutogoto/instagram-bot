from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import sqlite3
import os
import time
import sys
import logging
from pathlib import Path
import requests
import json
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# .envファイルから環境変数を読み込む
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

def getkey(url):
    """URLからキャッシュキーを抽出"""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get('ig_cache_key', [None])[0]

def getkey_blob(url):
    try:    
        # URLをパスセグメントに分割
        # クエリパラメータを除去
        path = url.split('?')[0]
        # プロトコルとドメインを除去
        if '//' in path:
            path = path.split('//')[1].split('/', 1)[1]
            
        segments = [seg for seg in path.split('/') if seg]
        
        # キーを含むセグメントは末尾
        if segments:
            last_segment = segments[-1]
            
            # .mp4を除去し、必要に応じて_video_dashinitも除去
            key = last_segment.split('.mp4')[0]
            if '_video_dashinit' in key:
                key = key.split('_video_dashinit')[0]
                
            if key:
                return key
                
        raise ValueError("Could not find key in URL path")
        
    except Exception as e:
        print(f'キーの抽出に失敗しました: {str(e)}')
        return None

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



def download_media(logger, url, username, type):    
    try:
        user_dir = os.path.join("media", username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            print(f'フォルダを作成しました: {user_dir}')
            
        # ファイル名を生成（ユーザー名フォルダ配下）
        time.sleep(2)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = os.path.join(user_dir, f"{username}_{timestamp}.{type}")

        # 動画のダウンロード
        print(f'ダウンロードを開始します: {filename}')
        logger.info(f'ダウンロードを開始します: {filename}')
        response = requests.get(url)
        response.raise_for_status()
        
        # ファイルとして保存
        with open(filename, 'wb') as f:
            f.write(response.content)
            
        print(f'ダウンロード完了: {filename}')
        logger.info(f'ダウンロード完了: {filename}')

        if(type == "jpg"):   
            extend_image_to_size(logger, filename)

        return True
        
    except Exception as e:
        print(f'メディアダウンロードでエラーが発生しました: {str(e)}')
        logger.error(f'メディアダウンロードでエラーが発生しました: {str(e)}')
        if os.path.exists(filename):
            os.remove(filename)
        return False

def get_complete_media_url(urls):
    from urllib.parse import urlparse, parse_qs
    
    # 最大のbyteendを持つURLを見つける
    max_byteend = 0
    max_byteend_url = None
    
    for url in urls:
        params = parse_qs(urlparse(url).query)
        byteend = int(params.get('byteend', [0])[0])
        if byteend > max_byteend:
            max_byteend = byteend
            max_byteend_url = url
    
    if not max_byteend_url:
        return None
        
    # 最大byteendのURLのbytestartを0に変更
    return max_byteend_url.split('bytestart')[0] + f"bytestart=0&byteend={max_byteend}"

def extract_request_urls(logs):
    request_urls = set()

    for entry in logs:
        try:
            message = json.loads(entry.get('message', '{}'))
            if 'message' not in message:
                continue
                
            # Request URLを含む部分を取得
            params = message.get('message', {}).get('params', {})
            if 'request' in params:
                request = params['request']
                url = request.get('url', '')
                
                # メディアURLのフィルタリング
                if ('scontent' in url and 
                    # '/v/t16/' in url and 
                    '.mp4' in url):  # 部分的なリクエストを除外
                    
                    request_urls.add(url)
                
        except (json.JSONDecodeError, KeyError):
            continue
    
    return list(request_urls)


def wait_for_lock(logger, max_wait_minutes):
    script_dir = Path(__file__).parent
    lock_dir = script_dir / 'lock'
    lock_dir.mkdir(exist_ok=True)
    lock_file = lock_dir / 'glink.lock'
    
    wait_start = time.time()
    logger.info("ロックファイルをチェックします")
    
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


from PIL import Image
def extend_image_to_size(logger, image_path, output_path=None, target_width=400, target_height=300):
    """
    画像のサイズが指定サイズより小さい場合、黒で拡張する
    output_pathが指定されない場合は、元の画像を上書きする
    """
    try:
        # output_pathが指定されていない場合は入力パスを使用
        output_path = output_path or image_path
        
        # 画像を開く
        img = Image.open(image_path)
        original_img = img.copy()  # 元の画像のバックアップを作成
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        current_width, current_height = img.size
        
        if logger:
            logger.info(f"元の画像サイズ: {current_width}x{current_height}")
        
        new_width = max(current_width, target_width)
        new_height = max(current_height, target_height)
        
        if new_width > current_width or new_height > current_height:
            try:
                new_img = Image.new('RGB', (new_width, new_height), 'black')
                x = (new_width - current_width) // 2
                y = (new_height - current_height) // 2
                new_img.paste(img, (x, y))
                
                # 保存
                new_img.save(output_path, 'JPEG', quality=95)
                return True
                
            except Exception as e:
                if output_path == image_path:
                    # 処理に失敗した場合、元の画像を復元
                    original_img.save(image_path)
                raise e
        else:
            if logger:
                logger.info("サイズ変更は不要です")
            if output_path != image_path:  # パスが異なる場合のみコピー
                img.save(output_path, 'JPEG', quality=95)
            return False
            
    except Exception as e:
        if logger:
            logger.error(f"画像処理中にエラーが発生: {str(e)}")
        raise

########## メイン　##########
def main():
    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        print("必要な引数が不足しています: USERNAMEが必要です")
        return 1

    USERNAME = sys.argv[1]

    logger = setup_logger(USERNAME)
    logger.info("処理開始")
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
            time.sleep(3)

        except Exception as e:
            error_msg = f"実行中にエラーが発生しました: {e}"
            logger.error(error_msg)
            print(error_msg)
            driver.quit()
            return 1
        
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


        ########## プロフィール写真をクリック(ストーリーチェック) ##########
        try:
            xpath = f"//img[contains(@alt, '{USERNAME}のプロフィール写真')]"
            profile_image = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            profile_image.click()
            logger.info("プロフィール写真のクリックに成功しました")

        except Exception as e:
            error_msg = f"プロフィール画像のクリックに失敗しました: {e}"
            logger.error(error_msg)
            print(error_msg)
            driver.quit()
            return 1

        ########## メディア取得 ##########
        #1.動画取得
        #2.なければ画像取得
        #3.なければ
        try:
            #video_check = driver.find_elements(
            #    By.XPATH,
            #    "//div[contains(@class, 'x10l6tqk')][@data-visualcompletion='ignore']"
            #)

            # 動画要素を待つ
            wait = WebDriverWait(driver, 3)
            video_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))
        
            if video_element:
                logger.info(f"{USERNAME}: 動画を検出しました")

                # 動画のsrcを取得
                video_src = video_element.get_attribute("src")
                # 動画をローカルに保存
                print(video_src)
                
                #driver.quit()


                #urls = get_video_urls(driver)
                
                time.sleep(1)
                # ネットワーク取得
                netlog = driver.get_log("performance")
                # url(部分的)取得
                urls = extract_request_urls(netlog)
                # url結合
                url = get_complete_media_url(urls)
                print(url)
                logger.info(f"生成URL:{url}")

                result_blob = False
                if url:
                    logger.info("動画URLを取得しました")
                    cache_key = getkey_blob(url)
                    if cache_key is None: 
                        logger.error("Keyの取得に失敗しました")
                        driver.quit()
                        return 1

                    result_blob = checkRecord(USERNAME, cache_key, url, logger)

                if(result_blob):
                    # 動画DL
                    download_media(logger, url, USERNAME, "mp4")
                else:
                    driver.quit()
                    return 1

                driver.quit()
                logger.info("処理終了")
                return 0


        except Exception as e:
            #error_msg = f"動画の取得に失敗しました: {e}"
            error_msg = f"動画の取得に失敗しました"
            logger.info(error_msg)
            print(error_msg)

            try:
                # 画像要素の取得
                target_classes = ["xl1xv1r", "x5yr21d", "xmz0i5r", "x193iq5w", "xh8yej3"]
                class_condition = " and ".join([f"contains(@class, '{cls}')" for cls in target_classes])
                xpath = f"//img[{class_condition} and contains(@alt, 'Photo by')]"

                image_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                image_url = image_element.get_attribute('src')

                result = False 
                if image_url:
                    logger.info("画像URLを取得しました")
                    cache_key = getkey(image_url)
                    result = checkRecord(USERNAME, cache_key, image_url, logger)
                
                print(image_url)
                # 画像DL
                if result:
                    download_media(logger, image_url, USERNAME, "jpg")

                else:
                    driver.quit()
                    return 1

                driver.quit()
                logger.info("処理終了")
                return 0
            
            except Exception as e:
                #error_msg = f"画像の取得に失敗しました: {e}"
                error_msg = "画像の取得に失敗しました"
                logger.info(error_msg)
                print(error_msg)
                driver.quit()
                logger.info("処理終了")
                return 1
    
    finally:
        # このブロックは必ず実行される
        if lock_file and lock_file.exists():
            try:
                lock_file.unlink()
                logger.info("ロックファイルを削除しました")
            except Exception as e:
                logger.error(f"ロックファイル削除時のエラー: {e}")

if __name__ == "__main__":
    result = main()
    sys.exit(result)