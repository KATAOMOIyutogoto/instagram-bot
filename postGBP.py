# 標準ライブラリ
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import subprocess

# Selenium関連
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

# サードパーティライブラリ
from dotenv import load_dotenv
import undetected_chromedriver as uc
import ssl 
import cv2  # 追加：動画サイズ確認用
import shutil  # 追加：ファイルコピー用

load_dotenv()


def ensure_video_resolution(file_path, logger, min_width=400, min_height=300):
    try:
        # 動画サイズを取得
        cap = cv2.VideoCapture(file_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        logger.info(f"元の動画サイズ: {width}x{height}")

        # 幅と高さが最小サイズ以上、かつ偶数なら変換不要
        if width >= min_width and height >= min_height and width % 2 == 0 and height % 2 == 0:
            logger.info("動画のサイズは要件を満たしており変換不要です")
            return file_path

        logger.info("動画のサイズが要件を満たしていないため変換を実施します")

        # 変換後のファイル名
        base, ext = os.path.splitext(file_path)
        resized_file = f"{base}_resized{ext}"

        # FFmpegで変換（Googleの最低要件 + H.264の偶数制限）
        command = [
            "ffmpeg",
            "-i", file_path,
            "-vf", "scale='if(lt(iw,400),trunc(400/2)*2,trunc(iw/2)*2)':'if(lt(ih,300),trunc(300/2)*2,trunc(ih/2)*2)'",
            "-c:a", "copy",
            resized_file
        ]

        logger.info(f"ffmpegコマンド: {' '.join(command)}")

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            logger.error("ffmpeg stderr:\n" + result.stderr)
            raise RuntimeError("ffmpeg変換失敗")

        logger.info(f"変換完了: {resized_file}")

        # 元ファイルを削除
        try:
            os.remove(file_path)
            logger.info(f"元ファイルを削除しました: {file_path}")
        except Exception as delete_error:
            logger.warning(f"元ファイルの削除に失敗しました: {delete_error}")

        return resized_file

    except Exception as e:
        logger.error(f"動画の変換に失敗しました: {e}")
        return file_path

### ロガーの設定 ###
def setup_logger(mode, username):

    script_name = mode.lower()  # "post" or "story"
    current_date = datetime.now().strftime("%Y%m%d")

    log_dir = Path(__file__).parent / "log" / current_date
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{script_name}_{username}_{current_date}.log"

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger = logging.getLogger(f"GBPPoster_{username}")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)

    separator = "=" * 80
    if os.path.exists(log_file):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{separator}\n")

    return logger


### 対象のGBPの投稿画面に遷移 ###
def create_business_post(business_id, logger):
    encoded_param = encode_google_business_param(business_id)
    url = f"https://business.google.com/locations/search?hl=ja&lq={encoded_param}"
    logger.info(f"エンコードURL:{url}")
    driver = get_chrome_driver_v2(logger)
    if driver is None:
        logger.error("Chromeドライバーの取得に失敗しました")
        return None
    driver.get("https://www.google.com/")
    time.sleep(3)  # 遷移を待機
    driver.get(url)
    time.sleep(5)  # 遷移を待機

    try:
        wait = WebDriverWait(driver, 10)
        # 投稿を作成ボタンの要素を待機して取得
        post_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[jsname="nFHyHb"]')))
        # ボタンをクリック
        post_button.click()
        time.sleep(3)  # 遷移を待機
        return driver

    except Exception as e:
        logger.error(f"Error: {e}")
        driver.quit()
        return None


### 対象のGBPパラメーターの取得 ###
def encode_google_business_param(business_id):
    param_list = [None, None, None, 1, None, None, business_id]
    json_str = json.dumps(param_list)
    encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    # base64のパディング(=)をピリオド(.)に置換
    return encoded.rstrip("=") + "."


###  Selenium Chrome Driverのセットアップ ###
def get_chrome_driver_v2(logger):
    
    subprocess.run("taskkill /F /IM chrome.exe", shell=True)
    load_dotenv()
    chrome_options = Options()
    # .envから設定を読み込む
    user_data_dir = os.getenv("CHROME_PROFILE_PATH")
    profile_name = os.getenv("PROFILE_NAME_GBP")
    chrome_options.add_argument("--start-maximized")

    # オプションを設定
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--profile-directory={profile_name}")      

    # その他の必要なオプション
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--headless")

    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    chrome_options.add_experimental_option("detach", False)
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-service-autorun") 
    chrome_options.add_argument("--password-store=basic")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # chrome_options.add_argument("--remote-debugging-port=9222")

    # プリファレンス設定
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # パフォーマンスログの設定
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        error_msg = f"Chromeドライバーの設定でエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error("注意: Chromeを完全に終了してから実行してください")
        return None


### GBPにメディアをアップロード ###
def upload_images_to_post_v2(driver, media_folder, logger):
    try:
        if not switch_to_post_frame(driver):
            logger.error("iframe切り替え失敗")
            return False

        # メディアファイルの拡張子を定義
        media_extensions = (".mp4", ".mov", ".avi", ".wmv", ".png", ".jpg", ".jpeg")

        # フォルダ内のメディアファイルを探す
        media_files = [f for f in os.listdir(media_folder) if f.lower().endswith(media_extensions)]
        print(media_folder)
        print(media_files)
        if not media_files:
            logger.error("メディアファイルが見つかりませんでした")
            return False

        print(len(media_files))
        print(media_files)

        # media_file = media_files[0]
        file_path = ""

        for media_file in media_files:
            try:
                # ファイル入力要素を待機（ループ内で毎回取得）
                file_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
                )

                # ファイルパスを取得
                file_path = os.path.abspath(os.path.join(media_folder, media_file))
                if file_path.lower().endswith((".mp4", ".mov", ".avi", ".wmv")):
                    file_path = ensure_video_resolution(file_path, logger)
                logger.info(f"アップロード中のファイル: {file_path}")

                # ファイルをアップロード
                file_input.send_keys(file_path)

                # ファイルタイプに応じて待機時間を調整
                if file_path.lower().endswith((".mp4", ".mov", ".avi", ".wmv")):
                    print("動画のアップロードを待機中...")
                    wait_time = 10
                else:
                    print("画像のアップロードを待機中...")
                    wait_time = 3

                # アップロード完了を待機
                time.sleep(wait_time)

            except Exception as e:
                logger.error(f"{media_file} のアップロード中にエラーが発生しました: {str(e)}")

        return driver, file_path

    except Exception as e:
        logger.error(f"アップロード処理中にエラーが発生しました: {str(e)}")
        return False

### iframe切り替え ###
def switch_to_post_frame(driver):
    try:
        # iframeが読み込まれるまで待機
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))

        time.sleep(3)

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


### 説明文取得 ###
def get_description(username, logger, process_id):

    description_dir = os.path.join("media", username, "description")
    temp_file_path = os.path.join(description_dir, f"{process_id}")

    try:
        with open(temp_file_path, "r", encoding="utf-8") as f:
            data = f.read()

        # backup_temp_file(username, process_id)
        return data

    except FileNotFoundError:
        logger.info(f"一時ファイルが見つかりません: {temp_file_path}")
        return None

    except Exception as e:
        logger.error(f"ファイル読み込みエラー: {str(e)}")
        return None

def _set_textarea_value_via_js(driver, el, text):
    # 絵文字を含むUTF-8文字列をBase64で渡し、JS側でUTF-8として復元してvalueに設定
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    script = r"""
        (function(el, b64){
          const bin = atob(b64);
          const bytes = new Uint8Array(bin.length);
          for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
          const text = new TextDecoder('utf-8').decode(bytes);
          el.value = text;
          el.dispatchEvent(new Event('input',  { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        })(arguments[0], arguments[1]);
    """
    driver.execute_script(script, el, b64)

### フォーム入力 ###
def fill_post_form(driver, description, logger):
    try:
        # 説明文入力フィールドを探す
        if description is not None:
            logger.info("Waiting for description field...")
            description_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[jsname="YPqjbf"]'))
            )
            logger.info("Setting description via JS (no send_keys)...")
            # 念のためクリア
            driver.execute_script("arguments[0].value='';", description_field)
            _set_textarea_value_via_js(driver, description_field, description)

            # 入力反映待ちの小休止（UI都合）
            time.sleep(1)


        # ボタンの追加セクションを探してクリック
        logger.info("Looking for button section...")
        button_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jscontroller="oIpQqb"]'))
        )
        button_dropdown.click()
        time.sleep(2)
        
        button_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-haspopup="true"]'))
        )
        button_dropdown.click()
        time.sleep(2)

        # CALLオプションを選択
        #logger.info("Selecting CALL option...")
        #call_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li[value="CALL"]')))
        #call_option.click()
        #time.sleep(1)

        # CALLオプションを選択（存在する場合のみ）
        try:
            logger.info("Trying to select CALL option...")
            call_option = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li[value="CALL"]')))
            call_option.click()
            logger.info("CALL option successfully selected")
            time.sleep(2)
        except Exception as call_error:
            logger.info(f"CALL option not found or not clickable: {call_error}")
            # ドロップダウンを閉じる（再度同じボタンをクリック）
            try:
                button_dropdown.click()
                time.sleep(2)
            except:
                # ドロップダウンを閉じられなくても続行
                logger.info("Could not close dropdown menu, continuing anyway")
                pass

        # 投稿ボタンをクリック
        logger.info("Clicking submit button...")
        submit_button = WebDriverWait(driver, 10).until(
            # EC.element_to_be_clickable((By.CSS_SELECTOR, '[jsname="vdQQuc"]'))
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jsname="PtNcAd"]'))
        )
        submit_button.click()
        time.sleep(3)

        return True

    except Exception as e:
        logger.error(f"Error filling form: {e}")
        return False


### メイン ###
def main():
    # コマンドライン引数の処理
    if len(sys.argv) < 4:
        sys.exit(1)

    mode = sys.argv[1]
    username = sys.argv[2]
    business_id = sys.argv[3]
    process_id = sys.argv[4]

    # ロガーのセットアップ
    logger = setup_logger(mode, username)

    # メディアフォルダのパス設定
    media_folder = os.path.join("media", username)

    logger.info(f"処理開始: Mode={mode}, Username={username}, GBP={business_id}")

    try:
        # GBP投稿画面を開く
        driver = create_business_post(business_id, logger)
        if not driver:
            logger.error("投稿画面オープン失敗")
            return 1

        # メディアアップロード
        upload_result = upload_images_to_post_v2(driver, media_folder, logger)
        if not upload_result:
            logger.error("メディアアップロード失敗")
            driver.quit()
            return 1

        driver, filepath = upload_result

        # 説明文の取得
        description = get_description(
            # mode=mode,
            username=username,
            logger=logger,
            # filepath=filepath,
            process_id=process_id,
        )

        # フォーム入力と投稿
        if not fill_post_form(driver, description, logger):
            logger.error("フォーム送信失敗")
            return 1

        # 投稿完了後の処理
        time.sleep(3)
        driver.quit()
        logger.info("処理完了")
        return 0

    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}")
        return 1


if __name__ == "__main__":
    result = main()
    sys.exit(result)
