import json
import base64
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from dotenv import load_dotenv
import sys
import shutil
import logging
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import TimeoutException, NoSuchElementException


# .envファイルから環境変数を読み込む
load_dotenv()

def setup_logger(username):
    # スクリプトのファイル名を取得（拡張子なし）
    #script_name = Path(__file__).stem
    script_name = "post"
    
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

def encode_google_business_param(business_id):
    param_list = [None, None, None, 1, None, None, business_id]
    json_str = json.dumps(param_list)
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    # base64のパディング(=)をピリオド(.)に置換
    return encoded.rstrip('=') + '.'

def setup_chrome_driver():
    chrome_options = Options()

    # .envから設定を読み込む
    user_data_dir = os.getenv('CHROME_PROFILE_PATH')
    profile_name = os.getenv('PROFILE_NAME_GBP')
    # オプションを設定
    chrome_options.add_argument(f'user-data-dir={user_data_dir}')
    chrome_options.add_argument(f'--profile-directory={profile_name}')

    #headless
    chrome_options.add_argument("--headless")

    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=chrome_options)


import psutil
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
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
    profile_name = os.getenv('PROFILE_NAME_GBP')


    chrome_options.add_argument("--start-maximized")
   
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
    #chrome_options.add_argument(f'--window-position={(port - 9222) * 100},0')  # ウィンドウ位置を分離

    
   
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





def switch_to_post_frame(driver):
    try:
        # iframeが読み込まれるまで待機
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        
        # すべてのiframeを取得
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Found {len(frames)} frames")
        
        # 各フレームを試行
        for frame in frames:
            try:
                driver.switch_to.frame(frame)
                # ファイル入力要素の存在を確認
                file_input = driver.find_element(By.CSS_SELECTOR, 'input.u5Dfnd[type="file"]')
                print("Found correct frame")
                return True
            except:
                driver.switch_to.default_content()
                continue
                
        print("Could not find the correct frame")
        return False
    except Exception as e:
        print(f"Error switching frames: {e}")
        return False

def upload_images_to_post(logger, driver, media_folder):
    try:
        if not switch_to_post_frame(driver):
            return False
        
        # メディアファイルの拡張子を定義
        media_extensions = ('.mp4', '.mov', '.avi', '.wmv', '.png', '.jpg', '.jpeg')
        
        # フォルダ内のメディアファイルを探す
        media_files = [f for f in os.listdir(media_folder) if f.lower().endswith(media_extensions)]
        
        if not media_files:
            logger.error("メディアファイルが見つかりませんでした")
            print("メディアファイルが見つかりませんでした")
            return False
        
        print(len(media_files))
        print(media_files)

        
        for media_file in media_files:
            try:
                # ファイル入力要素を待機（ループ内で毎回取得）
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )
                
                # ファイルパスを取得
                file_path = os.path.abspath(os.path.join(media_folder, media_file))
                print(f"アップロード中のファイル: {media_file}")
                logger.info(f"アップロード中のファイル: {media_file}")
                
                # ファイルをアップロード
                file_input.send_keys(file_path)
                
                # ファイルタイプに応じて待機時間を調整
                if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.wmv')):
                    print("動画のアップロードを待機中...")
                    wait_time = 10
                else:
                    print("画像のアップロードを待機中...")
                    wait_time = 3
                
                # アップロード完了を待機
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"{media_file} のアップロード中にエラーが発生しました: {str(e)}")
                logger.error(f"{media_file} のアップロード中にエラーが発生しました: {str(e)}")
                
                continue
        
        return driver
        
    except Exception as e:
        print(f"アップロード処理中にエラーが発生しました: {str(e)}")
        logger.error(f"アップロード処理中にエラーが発生しました: {str(e)}")
        return None

def encode_image(image_path):
    """画像をbase64エンコードする関数"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def fill_post_form(driver, description, logger):
    try:
        # 説明文入力フィールドを探す
        if description:
            logger.info("Waiting for description field...")
            description_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[jsname="YPqjbf"]'))
            )
            logger.info("Entering description...")
            description_field.clear()

            driver.execute_script(
                "arguments[0].value = arguments[1]", 
                description_field, 
                description
            )

            time.sleep(2)

        # ボタンの追加セクションを探してクリック
        logger.info("Looking for button section...")
        button_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-haspopup="true"]'))
        )
        button_dropdown.click()
        time.sleep(2)

        

        try:
            call_option = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'li[value="CALL"]'))
            )
            logger.info("CALL option found, clicking...")
            call_option.click()
        
        except TimeoutException:
            # CALLオプションが見つからない場合は「なし」をクリック
            logger.info("CALL option not found, selecting 'なし' option...")
            none_option = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//li//span[contains(text(), 'なし')]"))
            )
            none_option.click()




        # 投稿ボタンをクリック
        logger.info("Clicking submit button...")
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[jsname="vdQQuc"]'))
        )
        submit_button.click()
        time.sleep(3)

        return driver
    
    except Exception as e:
        logger.error(f"Error filling form: {e}")
        return None
    
def backup_media_files(source_dir):
    try:
        # 親ディレクトリのパスを取得
        parent_dir = os.path.dirname(source_dir)
        
        # media_bkディレクトリのパスを作成（親ディレクトリ配下）
        backup_dir = os.path.join(parent_dir, 'media_bk')
        
        # メディアファイルの拡張子
        media_extensions = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')
        
        # ディレクトリ内のファイルを処理
        files_moved = 0
        for filename in os.listdir(source_dir):
            if filename.lower().endswith(media_extensions):
                source_path = os.path.join(source_dir, filename)
                backup_path = os.path.join(backup_dir, filename)
                
                # ファイルを移動
                shutil.move(source_path, backup_path)
                files_moved += 1
                print(f'移動完了: {filename}')
        
        print(f'合計 {files_moved} 個のファイルを移動しました')
        return True
        
    except Exception as e:
        print(f'エラーが発生しました: {str(e)}')
        return False

##### 該当GBPの投稿ボタン押下 #####
def create_business_post(business_id, logger):
    encoded_param = encode_google_business_param(business_id)
    url = f"https://business.google.com/locations/search?hl=ja&lq={encoded_param}"
    print(url)
    logger.info(f"エンコードURL:{url}")
    
    #driver = setup_chrome_driver()
    driver = get_chrome_driver_v2(logger)



    driver.get(url)
   
    try:
        wait = WebDriverWait(driver, 10)
        # 投稿を作成ボタンの要素を待機して取得
        post_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[jsname="nFHyHb"]'))
        )
        # ボタンをクリック
        post_button.click()
        time.sleep(3)  # 遷移を待機

        return driver
    
    except Exception as e:
        print(f"Error: {e}")
        driver.quit()
        return None

def backup_temp_file(username, process_id):
    """一時ファイルをバックアップディレクトリに移動する"""
    # 元のファイルパス
    description_dir = os.path.join('media', username, 'description')
    temp_file_path = os.path.join(description_dir, f'{process_id}')
    
    # バックアップディレクトリのパス
    backup_dir = os.path.join('media', 'media_bk', 'description')
    
    # タイムスタンプを含むバックアップファイル名を生成
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    backup_file_name = f'{username}_{process_id}_{timestamp}'
    backup_path = os.path.join(backup_dir, backup_file_name)
    
    try:
        shutil.move(temp_file_path, backup_path)
        return True
    except Exception as e:
        print(f"バックアップ作成エラー: {str(e)}")
        return False

def read_temp_file(username, process_id):
    """一時ファイルを読み込んで削除する"""
    description_dir = os.path.join('media', username, 'description')
    temp_file_path = os.path.join(description_dir, f'{process_id}')
    
    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        # 一時ファイルを削除
        #os.remove(temp_file_path)
        # バックアップ作成
        backup_temp_file(username, process_id)
        
        return data
    except FileNotFoundError:
        print(f"一時ファイルが見つかりません: {temp_file_path}")
        return None
    except Exception as e:
        print(f"ファイル読み込みエラー: {str(e)}")
        # エラー時でもファイルが存在する場合は削除を試みる
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        return None

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


def main():
    # コマンドライン引数の処理
    if len(sys.argv) < 3:
        print("必要な引数が不足しています: USERNAME, process_idが必要です")
        return

    USERNAME = sys.argv[1]
    business_id = os.getenv(USERNAME)
    #business_id = "16739471645260047887"
    process_id = sys.argv[2]

    logger = setup_logger(USERNAME)
    logger.info(f"処理開始 PROCESSID:{process_id}")
    logger.info(f"対象ユーザー: {USERNAME}")

    image_folder = rf"C:\Users\avd-admin-go2\Desktop\MEO\dev\media\{USERNAME}"  # 画像フォルダのパスを指定
    #description = "ここに投稿の説明文を入力してください" 


    lock_file = None
    try:

        ##### lock処理 #####
        lock_file = wait_for_lock(logger, max_wait_minutes=30)
        logger.info("処理を開始します")


        # 該当GBPの投稿ボタン押下
        open_driver = create_business_post(business_id, logger)
        if not open_driver:
            print("Failed to open")
            logger.error("投稿ボタン押下失敗")
            return 1
        else:
            logger.info("投稿ボタンを押下しました")

        # メディアアップロード
        upload_driver = upload_images_to_post(logger, open_driver, image_folder)
        if not upload_driver:
            logger.error("メディアアップロード失敗")
            return 1
        else:
            logger.info("メディアをアップロードしました")

        #time.sleep(5)

        # 一時ファイルから投稿URLを読み込む（読み込み後に削除）
        description = read_temp_file(USERNAME, process_id)
        if description is None:
            description = ""
            
        print(f"説明文: {description}")

            # フォーム入力、投稿
            #form_driver = fill_post_form(upload_driver, description)

        form_driver = fill_post_form(upload_driver,description, logger)        
        if not form_driver:
            logger.error("フォーム送信失敗")
            return 1
        else:
            logger.info("フォームを送信しました")
    
        # メディア移動
        if form_driver:
            time.sleep(3)
            open_driver.quit()

            result_backup = backup_media_files(image_folder)
            if not result_backup:
                print("Failed to backup")
                logger.error("バックアップ失敗")
                return 1
            
            return 0
        
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