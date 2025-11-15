# 標準ライブラリのインポート
import io
import logging
import os
import random
import sys
import time
import shutil
import tempfile
from datetime import datetime as dt, timezone, timedelta

from pathlib import Path
import re, html
import time as _time


# Seleniumに関連するインポート
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# 自作モジュールのインポート
from story import (
    download_media,
    extract_request_urls_v2,
    get_complete_media_url,
    getkey_blob,
    checkRecord,
    getkey,
    extract_datetime
)

# 標準出力のエンコーディングをUTF-8に設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# サードパーティのライブラリインポート
from dotenv import load_dotenv

load_dotenv()
MAX_AGE_DAYS = 3

### Loggerセットアップ ###
def setup_logger(username):
    # スクリプトのファイル名を取得（拡張子なし）
    script_name = Path(__file__).stem

    # 現在の日付を取得
    current_date = dt.now().strftime("%Y%m%d")

    # logディレクトリと日付ディレクトリのパスを作成
    log_dir = Path(__file__).parent / "log" / current_date
    log_dir.mkdir(parents=True, exist_ok=True)

    # 現在の日付でログファイル名を生成（ユーザー名を含める）
    log_file = log_dir / f"{script_name}_{username}_{current_date}.log"

    # ログフォーマットの設定
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # ファイルハンドラの設定
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # ロガーの設定
    logger = logging.getLogger(f"InstagramScraper_{username}")
    logger.setLevel(logging.INFO)

    # 既存のハンドラをクリア（同じユーザーの複数回の実行で重複を防ぐ）
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)

    # ログファイルに区切り線と開始メッセージを書き込む
    separator = "=" * 80
    start_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    if os.path.exists(log_file):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{separator}\n")

    return logger


### Seleniumセットアップ ###
def get_chrome_driver_v2(logger):
    """Chromeドライバーの設定（並列実行対応）"""
    load_dotenv()
    chrome_options = Options()
    # .envから設定を読み込む
    base_path = os.getenv("CHROME_PROFILE_PATH")
    # プロファイルをランダムに選択
    profile_name, cookies_file = random.choice(
        [
            [os.getenv("PROFILE_NAME_1"),os.getenv("INSTAGRAM_COOKIE_1")],
            [os.getenv("PROFILE_NAME_2"),os.getenv("INSTAGRAM_COOKIE_2")],
            [os.getenv("PROFILE_NAME_3"),os.getenv("INSTAGRAM_COOKIE_3")],
            [os.getenv("PROFILE_NAME_4"),os.getenv("INSTAGRAM_COOKIE_4")],
        ]
    )
    logger.info(f"選択されたプロファイル: {profile_name}")

    # 完全なユーザーデータディレクトリのパスを構築
    user_data_dir = os.path.join(base_path, profile_name)
    logger.info(f"使用するパス: {user_data_dir}")

    # オプションを設定
    # リモートデバッグのためのオプション修正
    chrome_options.add_argument(f"--user-data-dir={base_path}")
    chrome_options.add_argument(f"--profile-directory={profile_name}")      
    chrome_options.add_argument("--remote-debugging-port=9222")

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
    chrome_options.add_argument("--lang=ja-JP")  # ← 追加（日本語UIを優先）

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
        return driver, cookies_file
    except Exception as e:
        error_msg = f"Chromeドライバーの設定でエラーが発生しました: {e}"
        logger.error(error_msg)
        logger.error("注意: Chromeを完全に終了してから実行してください")
        return None

# --- 追加: ピン留め判定 ---
def _is_pinned_post(card):
    try:
        # SVGは namespace の都合で name()='svg' を使うと安定
        card.find_element(
            By.XPATH,
            ".//*[name()='svg' and (contains(@aria-label,'ピン') or contains(@aria-label,'Pinned'))]"
            " | .//*[name()='title' and (contains(.,'ピン留め') or contains(.,'Pinned'))]"
        )
        return True
    except NoSuchElementException:
        return False

# --- 追加: img alt から投稿日(ざっくり)を拾う（失敗したら None）---
def _date_from_card_alt(card):
    try:
        alt = card.find_element(By.CSS_SELECTOR, "img[alt]").get_attribute("alt") or ""
        # 例: "Photo by xxx on September 16, 2024." を拾う
        m = re.search(r"on\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", alt)
        if m:
            mon, day, year = m.groups()
            return dt.strptime(f"{mon} {day} {year}", "%B %d %Y")
    except Exception:
        pass
    return None

# --- 追加: 投稿URLから厳密な投稿日を取って「N日より古いか」確認 ---
def _is_older_than_days(driver, url, days, wait):
    current = driver.current_url
    try:
        driver.get(url)
        t = wait.until(EC.presence_of_element_located((By.TAG_NAME, "time")))
        iso = t.get_attribute("datetime")
        if iso:
            posted = dt.fromisoformat(iso.replace("Z", "+00:00"))
            return (dt.now(timezone.utc) - posted) > timedelta(days=days)
    finally:
        driver.back()
        wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, 'a._a6hd[href*="/p/"], a._a6hd[href*="/reel/"]')
        ))
    return False

def get_page_caption(driver, username, timeout=12):
    wait = WebDriverWait(driver, timeout)

    # ユーザー名リンクがDOMに出るまで待つ
    wait.until(EC.presence_of_element_located(
        (By.XPATH, f"//a[contains(@href,'/{username}/')]")
    ))

    XPATHS = [
        # 既存（残す）
        f"(//div[.//a[contains(@href,'/{username}/')] and .//time]"
        f"/following-sibling::span)[1]",

        f"(//a[contains(@href,'/{username}/')]/ancestor::div[1]"
        f"/following-sibling::span)[1]",

        f"(//div[.//a[contains(@href,'/{username}/')]]"
        f"//time/parent::span/following-sibling::span)[1]",

        # 追加: time を起点に「次に現れるキャプション候補」を広めに拾う
        # 兄弟 → それ以降 の順で探索
        "(//time/ancestor::div[1]/following-sibling::*"
        "//h1[contains(@class,'_ap3a')] | "
        "//time/ancestor::div[1]/following-sibling::*"
        "//span[contains(@class,'_ap3a')])[1]",

        # 追加: time から前進して最初の「テキストを持つ span」
        "(//time/ancestor::div[1]/following::span"
        "[normalize-space()][1])",

        # 追加: ハッシュタグの a が含まれるブロックの直近の親（タグが無い投稿でも次の候補が当たるため前のXPATHで拾える）
        "(//a[contains(@href,'/explore/tags')]/ancestor::span[1])[1]",
    ]

    cap_el = None
    for xp in XPATHS:
        try:
            el = wait.until(EC.presence_of_element_located((By.XPATH, xp)))
            txt = (el.get_attribute("innerText") or "").strip()
            if not txt:
                # 中身が空のラッパ要素対策：子要素側の可視テキストを読む
                txt = (el.text or "").strip()
            if txt:
                cap_el = el
                break
        except Exception:
            continue

    if cap_el is None:
        return None

    # 「もっと見る」を広めに検出（言語違い・三点リーダ対応）
    try:
        more = cap_el.find_element(
            By.XPATH,
            ".//*[contains(text(),'もっと見る') or contains(text(),'more') or contains(text(),'See more') or contains(.,'…')]"
        )
        driver.execute_script("arguments[0].click()", more)
        # 展開後にテキストが増えるまで少し待つ
        WebDriverWait(driver, 3).until(
            lambda d: (cap_el.get_attribute('innerText') or cap_el.text or '').strip() != ''
        )
    except Exception:
        pass

    txt = (cap_el.get_attribute("innerText") or cap_el.text or "").strip()
    return html.unescape(txt)


def get_caption_by_username(driver, username, logger=None, timeout=12):
    has_dialog = bool(driver.find_elements(By.XPATH, "//div[@role='dialog']"))
    if has_dialog:
        root = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.XPATH,
                f"//div[@role='dialog']"
                f"//li[contains(@class,'_a9zj')][.//a[contains(@href,'/{username}/')]]"
            ))
        )
        # h1 でも span でもOKにする
        cap_el = None
        for xp in [
            ".//h1[contains(@class,'_ap3a')]",
            ".//span[contains(@class,'_ap3a')]",
            # 念のためフォールバック（テキストを持つ最初のspan）
            ".//span[normalize-space()][1]"
        ]:
            try:
                cap_el = root.find_element(By.XPATH, xp)
                if (cap_el.get_attribute("innerText") or cap_el.text or "").strip():
                    break
            except Exception:
                continue

        if cap_el:
            try:
                more = cap_el.find_element(By.XPATH, ".//*[contains(text(),'もっと見る') or contains(text(),'more') or contains(.,'…')]")
                driver.execute_script("arguments[0].click()", more)
            except Exception:
                pass
            return (cap_el.get_attribute("innerText") or cap_el.text or "").strip()

        # どうしても見つからなければページ版にフォールバック
        return get_page_caption(driver, username, timeout)

    # ダイアログでないとき
    return get_page_caption(driver, username, timeout)



### デバッグ用 ###
import json
def analyze_logs(logs):
    mp4_count = 0
    scontent_count = 0
    for entry in logs:
        message = json.loads(entry.get("message", "{}"))
        message_str = json.dumps(message)
        if ".mp4" in message_str:
            mp4_count += 1
        if "scontent" in message_str:
            scontent_count += 1
    
    print(f"MP4を含むログエントリ: {mp4_count}")
    print(f"scontentを含むログエントリ: {scontent_count}")
    
    # 最初のMP4とscontentを含むエントリを表示
    for entry in logs:
        message = json.loads(entry.get("message", "{}"))
        message_str = json.dumps(message)
        if ".mp4" in message_str:
            print("最初のMP4エントリ:")
            print(message_str[:500] + "...")  # 最初の500文字のみ表示
            break


### メイン ###
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
    logger.info("処理を開始します")

    driver,cookies_file = get_chrome_driver_v2(logger)
    if not driver:
        logger.error("Chromeドライバーの初期化に失敗しました")
        return 1

    ########## Instagramのプロフィールページにアクセス ##########
    try:
        logger.info(f"{USERNAME} のプロフィールページにアクセスします")
        driver.get(f"https://www.instagram.com/{USERNAME}/?hl=ja")
        time.sleep(10)
        # # cookieの読み込み
        # json_open = open(cookies_file, 'r') 
        # cookies = json.load(json_open) 
        # for cookie in cookies: 
        #     tmp = {"name": cookie["name"], "value": cookie["value"]} 
        #     driver.add_cookie(tmp) 
        # driver.get(f"https://www.instagram.com/{USERNAME}/?hl=ja")
        # time.sleep(10)

    except Exception as e:
        error_msg = f"実行中にエラーが発生しました: {e}"
        logger.error(error_msg)
        print(error_msg)
        driver.quit()
        return 1

    # Facebookのエラーページをチェック
    facebook_error_elements = driver.find_elements(
        By.XPATH,
        "//h1[contains(text(), 'Sorry, something went wrong')] | //div[@class='core']//p[contains(text(), 'working on getting this fixed')]",
    )
    if facebook_error_elements and facebook_error_elements[0].is_displayed():
        logger.error("アカウントの自動化が検出された可能性があります")
        return 3

    # ページが利用できない場合のメッセージをチェック
    unavailable_elements = driver.find_elements(
        By.XPATH,
        "//span[contains(text(), 'このページはご利用いただけません')] | //span[contains(text(), 'リンクに問題があるか、ページが削除された可能性があります')]",
    )
    if unavailable_elements and unavailable_elements[0].is_displayed():
        logger.error("ユーザネームの変更、またはブロックされた可能性があります")
        return 1

    # エラーページのチェック
    error_elements = driver.find_elements(
        By.XPATH,
        "//span[contains(text(), 'エラーが発生しました')] | //span[contains(text(), '問題が発生したため、ページを読み込めませんでした')]",
    )
    if error_elements and error_elements[0].is_displayed():
        logger.info("アカウントがロックされました")
        return 3  # または必要な戻り値

    # 投稿がない場合のメッセージの存在チェック
    no_posts_elements = driver.find_elements(By.XPATH, "//span[contains(text(), '投稿はまだありません')]")
    if no_posts_elements and no_posts_elements[0].is_displayed():
        logger.info("投稿はまだありません")
        return 1

    ########## 最新投稿読み込み ##########
    try:
        logger.info("最新投稿を読み込みます")

        time.sleep(5)

        wait = WebDriverWait(driver, 20)

        # プロフィールグリッドから投稿リンクを直接取得
        # プロフィールグリッドから投稿リンクを取得
        post_links = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, 'a._a6hd[href*="/p/"], a._a6hd[href*="/reel/"]')
            )
        )

        # まず href と「ピン留めかどうか」をリスト化（最初の12件くらい見れば十分）
        candidates = []
        for link in post_links[:12]:
            href = link.get_attribute("href") or ""
            if not href:
                continue
            pinned = _is_pinned_post(link)
            candidates.append((href, pinned))

        latest_post_url = None

        # 候補を順番にチェック
        for href, pinned in candidates:
            if not pinned:
                # 非ピン留めはそのまま採用
                latest_post_url = href
                logger.info(f"選定: 非ピン留め {href}")
                break

            # ピン留め → 日付を確認
            logger.info(f"候補はピン留め: {href} → 日付確認")
            driver.get(href)
            try:
                t = WebDriverWait(driver, 12).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
                dt_str = t.get_attribute("datetime") or ""
                if not dt_str:
                    logger.warning("time要素は見つかったが datetime属性なし → 採用（安全側）")
                    latest_post_url = href
                    break

                post_dt = dt.fromisoformat(dt_str.replace("Z", "+00:00"))
                now_utc = dt.now(timezone.utc)
                age = now_utc - post_dt

                if MAX_AGE_DAYS > 0 and age >= timedelta(days=MAX_AGE_DAYS):
                    logger.info(f"ピン留めだが3日以上前({age.days}日) → スキップ")
                    continue
                else:
                    logger.info("ピン留めだが3日以内 → 採用")
                    latest_post_url = href
                    break
            except Exception as e:
                logger.warning(f"ピン留め日付確認で例外: {e} → 採用（安全側）")
                latest_post_url = href
                break

        # 採用できたらそのページへ、できなければ次へ
        if latest_post_url:
            driver.get(latest_post_url)
            time.sleep(2)
            logger.info("最新投稿ページにアクセスしました")
        else:
            logger.info("条件に合致する投稿が見つかりませんでした（全部ピン留め3日超え等）")
            driver.quit()
            return 1

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
            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")

            # エラー情報保存用のディレクトリ
            error_dir = Path(__file__).parent / "error_shots"
            error_dir.mkdir(parents=True, exist_ok=True)

            # スクリーンショット保存
            screenshot_path = error_dir / f"error_{timestamp}.png"
            driver.save_screenshot(str(screenshot_path))

            # HTML保存
            html_path = error_dir / f"error_{timestamp}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)

            logger.info(f"エラー時の内容を保存しました")

        except Exception as save_error:
            logger.error(f"エラー情報の保存に失敗: {str(save_error)}")

    ########## 最新投稿の種別確認 ##########
    post_date = ""
    media_urls = []
    description = ""
    datetime_value=""
    try:
        # 要素が読み込まれるまで待機
        wait = WebDriverWait(driver, 20)

        try:

            # time要素を取得
            wait = WebDriverWait(driver, 10)
            time_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "time")))

            # datetime属性から日時を取得
            datetime_value = extract_datetime(driver, logger)
            if datetime_value:
                logger.info(f"{USERNAME} の投稿日時: {datetime_value}")
            date_str = time_element.get_attribute("datetime")
            if date_str is None:
                raise ValueError("datetime属性が見つかりません")

            date = dt.fromisoformat(date_str.replace("Z", "+00:00"))
            # 👇 追加：古い投稿を共通でスキップするガード（ピン留め/非ピン留め共通）
            max_age_days = int(os.getenv(f"{USERNAME}_max_age_days") or os.getenv("MAX_AGE_DAYS") or "0")
            if MAX_AGE_DAYS > 0:
                age = dt.now(timezone.utc) - date  # UTC同士で比較
                if age > timedelta(days=MAX_AGE_DAYS):
                    logger.info(f"投稿日が {MAX_AGE_DAYS}日より古いためスキップ: posted={date.isoformat()}, age={age}")
                    driver.quit()
                    return 1

            jst = timezone(timedelta(hours=+9), "JST")
            date_jst = date.astimezone(jst)  # JSTに変換
            post_date = date_jst.strftime("%Y%m%d")

            logger.info(f"date:{date_jst}")
            logger.info(f"post_date:{post_date}")
            print(f"post_date:{post_date}")

            start_date = os.getenv(f"{USERNAME}_start")
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
        expected_images = 0  
        # 複数動画は一旦サーバー負荷考慮で未対応にする
        try:
            video_element = driver.find_element(By.CSS_SELECTOR, "video.x1lliihq")
            # media_url = video_element.get_attribute('src')
            media_urls.append(video_element.get_attribute("src"))
            media_type = "video"

        except NoSuchElementException:
            ########## 複数画像_カルーセル ##########
            # -------- 複数画像 or 単一画像 --------
            wait = WebDriverWait(driver, 20)

            def _best_url_from_img(img):
                u = img.get_attribute("src")
                if not u:
                    ss = img.get_attribute("srcset")
                    if ss:
                        parts = [s.strip() for s in ss.split(",") if s.strip()]
                        try:
                            best = max(parts, key=lambda x: int(x.split()[-1].rstrip("w")))
                            u = best.split()[0]
                        except Exception:
                            u = parts[-1].split()[0] if parts else None
                return u if u and u.startswith("http") else None

            # ユニーク管理（重複排除）
            seen = set(media_urls)

            def _add(u, how):
                if u and u not in seen:
                    seen.add(u)
                    media_urls.append(u)
                    logger.info(f"検出({how}): {u}")
                    return True
                return False

            def _collect_from_ul():
                new = 0
                for img in driver.find_elements(By.CSS_SELECTOR, "ul._acay li._acaz img"):
                    _u = _best_url_from_img(img)
                    if _add(_u, "UL"):
                        new += 1
                return new

            def _current_main_src():
                el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._aagv img")))
                return _best_url_from_img(el)

            # 枚数の目安
            indicator_cnt = len(driver.find_elements(By.CSS_SELECTOR, "div._acnb"))
            ul_img_cnt = len(driver.find_elements(By.CSS_SELECTOR, "ul._acay li._acaz"))
            total_images = max(indicator_cnt, ul_img_cnt) or 1
            logger.info(f"カルーセル推定: {total_images}枚")

            # 初回：UL全体から直取り
            _collect_from_ul()

            if total_images > 1:
                # 次へで切り替え → UL再収集 を繰り返し（ユニーク数が目標に達するまで）
                tries = 0
                while len(seen) < total_images and tries < total_images + 5:
                    prev = _current_main_src()
                    try:
                        next_btn = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="次へ"]'))
                        )
                    except Exception:
                        # 念のため最後に直取りして終了
                        _collect_from_ul()
                        break

                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                    try:
                        next_btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", next_btn)

                    # 本当に画像が切り替わるまで待つ
                    try:
                        wait.until(
                            lambda d: (_best_url_from_img(d.find_element(By.CSS_SELECTOR, "div._aagv img")) or "")
                                      != (prev or "")
                        )
                    except Exception:
                        pass

                    time.sleep(0.3)  # 遅延ロード対策
                    _collect_from_ul()                  # UL全体から再収集
                    _add(_current_main_src(), "CLICK")  # 表示中の1枚も明示的に追加
                    tries += 1

                media_type = "image_carousel"
                expected_images = total_images

            else:
                # 単一画像
                img_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._aagv img")))
                _add(_best_url_from_img(img_el), "SINGLE")
                media_type = "image"
                expected_images = 1


        print(f"メディアタイプ: {media_type}")
        print("メディアURL:")
        for i, url in enumerate(media_urls, 1):
            print(f"{i}枚目: {url}")
            logger.info(f"{i}枚目: {url}")

        ########## 説明文取得 ##########
        try:
            logger.info("[caption/by_username] 開始")
           
            description = get_caption_by_username(driver, USERNAME, logger=logger, timeout=20)
            if description is None:
                raise RuntimeError("caption is None")

            if description == "":
                logger.info("[caption/by_username] 説明文は空（正常継続）")
            else:
                logger.info(f"[caption/by_username] 説明文確定（先頭100）: '{description[:100]}'")

            # 保存
            description_dir = os.path.join("media", USERNAME, "description")
            os.makedirs(description_dir, exist_ok=True)
            temp_file_path = os.path.join(description_dir, f"{process_id}")
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(description)
            logger.info(f"[caption/by_username] 説明文を保存: {temp_file_path}")

        except Exception as e:
            # 失敗時はダンプして終了（従来と同じ動作）
            dump_dir = Path(__file__).parent / "error_shots"
            dump_dir.mkdir(parents=True, exist_ok=True)
            dump = dump_dir / f"no_caption_{dt.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(dump, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.exception(f"[caption/by_username] 取得失敗。page_source保存: {dump}")
            driver.quit()
            return 1

    except Exception as e:
        print(f"最新投稿の要素読み込みでエラーが発生しました: {str(e)}")

    # メディア取得
    try:
        flg = False
        dl_images = 0           # 新規にDLできた画像の枚数
        skipped_existing = 0    # 既存レコードでスキップした枚数
        failed_images = 0       # 失敗カウント（例外等）
        for media_url in media_urls:
            # URLがblobで始まる場合の特別処理
            if media_url == media_url and media_url.startswith("blob:"):
                print("blobで始まるURLを検出しました")
                time.sleep(1)
                # ネットワーク取得
                netlog = driver.get_log("performance")

                #デバッグ用
                #analyze_logs(netlog)
                # url(部分的)取得
                #urls = extract_request_urls(netlog)
                urls = extract_request_urls_v2(netlog)

                # url結合
                complete_url = get_complete_media_url(urls)
                print(complete_url)
                logger.info(f"生成URL:{complete_url}")

                cache_key = getkey_blob(complete_url)
                if cache_key is None:
                    logger.error("Keyの取得に失敗しました")
                    driver.quit()
                    return 1

                result_blob = checkRecord(USERNAME, cache_key, complete_url, logger, datetime_value)
                if result_blob:
                    # 動画DL
                    download_media(logger, complete_url, USERNAME, "mp4")
                    flg = True
                else:
                    logger.info("このレコードは存在します")
                    # driver.quit()
                    # return 1
                    continue

            else:
                logger.info("画像URLを取得しました")
                cache_key = getkey(media_url)
                result = checkRecord(USERNAME, cache_key, media_url, logger, datetime_value)

                if result:
                    logger.info("メディアを取得します")
                    try:
                        download_media(logger, media_url, USERNAME, "jpg")
                        dl_images += 1
                        flg = True
                    except Exception as e:
                        failed_images += 1
                        logger.error(f"画像ダウンロード失敗: {e}")
                else:
                    skipped_existing += 1
                    logger.info("このレコードは存在します")
                    continue
        # 収集とDLの整合性チェック（カルーセルのみ厳しめに）
        if media_type == "image_carousel":
            extracted_images = len([u for u in media_urls if u and not u.startswith("blob:")])
            logger.info(
                f"カルーセル集計: 想定{expected_images} / 収集{extracted_images} / 新規DL{dl_images} / 既存スキップ{skipped_existing} / 失敗{failed_images}"
            )

            if extracted_images != expected_images:
                logger.info(
                    f"カルーセル取得不一致: 想定{expected_images}枚なのに収集{extracted_images}枚（新規DL{dl_images}, 既存{skipped_existing}, 失敗{failed_images}）"
                )
            elif dl_images == 0 and skipped_existing == expected_images and failed_images == 0:
                logger.info("カルーセル: すべて既存レコード（新規DLなし）。処理OK。")
            else:
                # 新規DL枚数が想定−既存とズレるときだけ注意喚起
                expected_new = max(expected_images - skipped_existing, 0)
                if dl_images != expected_new:
                    logger.error(
                        f"カルーセルDL数に差異: 期待{expected_new}枚 / 実際{dl_images}枚（既存{skipped_existing}, 失敗{failed_images}）"
                    )
        if not flg:
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


if __name__ == "__main__":
    result = main()

    # print(result)
    sys.exit(result)
