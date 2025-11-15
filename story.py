# 標準ライブラリのインポート
import base64
import io
import json
import logging
import os
import sqlite3
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from PIL import Image

# Seleniumに関連するインポート
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# AI サービス
from anthropic import Anthropic
from openai import OpenAI

# Google サービス
from google.cloud import videointelligence
from google.oauth2 import service_account

# サードパーティのライブラリインポート
import requests
from dotenv import load_dotenv

load_dotenv()


### Loggerセットアップ ###
def setup_logger(username):
    # スクリプトのファイル名を取得（拡張子なし）
    script_name = Path(__file__).stem

    # 現在の日付を取得
    current_date = datetime.now().strftime("%Y%m%d")

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
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


### 動画_URL部分取得_v1 ###
def extract_request_urls(logs):
    request_urls = set()

    for entry in logs:
        try:
            message = json.loads(entry.get("message", "{}"))
            if "message" not in message:
                continue

            # Request URLを含む部分を取得
            params = message.get("message", {}).get("params", {})
            if "request" in params:
                request = params["request"]
                url = request.get("url", "")

                # メディアURLのフィルタリング
                if (
                    "scontent" in url
                    and
                    # '/v/t16/' in url and
                    ".mp4" in url
                ):  # 部分的なリクエストを除外

                    request_urls.add(url)

        except (json.JSONDecodeError, KeyError):
            continue

    return list(request_urls)

### 動画_URL部分取得_v2 ###
def extract_request_urls_v2(logs):
    request_urls = set()
    for entry in logs:
        try:
            message = json.loads(entry.get("message", "{}"))
            if "message" not in message:
                continue
            # Request URLを含む部分を取得
            params = message.get("message", {}).get("params", {})
            if "request" in params:
                request = params["request"]
                url = request.get("url", "")
                # メディアURLのフィルタリング - scontentの条件を削除
                if ".mp4" in url:  # mp4ファイルのみをフィルタリング
                    #print(f"MP4 URL found: {url}")
                    request_urls.add(url)
        except (json.JSONDecodeError, KeyError):
            continue
    
    result = list(request_urls)
    print(f"Found {len(result)} media URLs")
    return result

### 動画_URL結合 ###
def get_complete_media_url(urls):
    from urllib.parse import urlparse, parse_qs

    # 最大のbyteendを持つURLを見つける
    max_byteend = 0
    max_byteend_url = None

    for url in urls:
        params = parse_qs(urlparse(url).query)
        byteend = int(params.get("byteend", [0])[0])
        if byteend > max_byteend:
            max_byteend = byteend
            max_byteend_url = url

    if not max_byteend_url:
        return None

    # 最大byteendのURLのbytestartを0に変更
    return max_byteend_url.split("bytestart")[0] + f"bytestart=0&byteend={max_byteend}"


### 動画_キー取得 ###
def getkey_blob(url):
    try:
        # URLをパスセグメントに分割
        # クエリパラメータを除去
        path = url.split("?")[0]
        # プロトコルとドメインを除去
        if "//" in path:
            path = path.split("//")[1].split("/", 1)[1]

        segments = [seg for seg in path.split("/") if seg]

        # キーを含むセグメントは末尾
        if segments:
            last_segment = segments[-1]

            # .mp4を除去し、必要に応じて_video_dashinitも除去
            key = last_segment.split(".mp4")[0]
            if "_video_dashinit" in key:
                key = key.split("_video_dashinit")[0]

            if key:
                return key

        raise ValueError("Could not find key in URL path")

    except Exception as e:
        print(f"キーの抽出に失敗しました: {str(e)}")
        return None


### 画像_キー取得 ###
def getkey(url):
    """URLからキャッシュキーを抽出"""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    cache_key = query_params.get("ig_cache_key", [None])[0]
        
    # Base64エンコードの終端マーカー(== または %3D%3D)以降をカット
    if '%3D%3D' in cache_key:
        return cache_key.split('%3D%3D')[0] + '%3D%3D'
    elif '==' in cache_key:
        return cache_key.split('==')[0] + '=='
    return cache_key


### DB重複チェック ###
def checkRecord(user_name, cache_key, media_url, logger, datetime_value):
    """データベースでレコードをチェックして保存（重複は非エラー扱い）。"""
    import traceback
    DBNAME = os.getenv("DB_NAME")
    TABLENAME = os.getenv("TABLE_NAME")

    conn = None
    last_sql = None
    last_params = None

    try:
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()

        # cache_key の正規化（None / 空文字 / 空白 → None）
        norm_key = (cache_key or "").strip() or None

        if norm_key is None:
            # ★ cache_key が無い → 日付のみで重複チェック（同一投稿は1件だけ許可）
            last_sql = f"SELECT 1 FROM {TABLENAME} WHERE user_name = ? AND datetime_value = ?"
            last_params = (user_name, datetime_value)
            cursor.execute(last_sql, last_params)
            exists = cursor.fetchone()

            if exists is None:
                last_sql = (f"INSERT INTO {TABLENAME} "
                            f"(user_name, cache_key, media_url, datetime_value) VALUES (?, ?, ?, ?)")
                last_params = (user_name, None, media_url, datetime_value)
                cursor.execute(last_sql, last_params)
                conn.commit()
                logger.info(f"INSERT(no-key): user={user_name}, dt={datetime_value}")
                return True
            else:
                logger.info(f"DUP(no-key by date): user={user_name}, dt={datetime_value}")
                return False

        else:
            # ★ cache_key がある → 投稿内で同一メディアのみ重複扱い
            last_sql = (f"SELECT 1 FROM {TABLENAME} "
                        f"WHERE user_name = ? AND datetime_value = ? AND cache_key = ?")
            last_params = (user_name, datetime_value, norm_key)
            cursor.execute(last_sql, last_params)
            exists = cursor.fetchone()

            if exists is None:
                last_sql = (f"INSERT INTO {TABLENAME} "
                            f"(user_name, cache_key, media_url, datetime_value) VALUES (?, ?, ?, ?)")
                last_params = (user_name, norm_key, media_url, datetime_value)
                cursor.execute(last_sql, last_params)
                conn.commit()
                logger.info(f"INSERT(with-key): user={user_name}, key={norm_key}, dt={datetime_value}")
                return True
            else:
                logger.info(f"DUP(with-key): user={user_name}, key={norm_key}, dt={datetime_value}")
                return False

    except sqlite3.IntegrityError as e:
        # ← ここだけ“普通のログ”に変更（stacktrace無し）
        if conn:
            conn.rollback()
        logger.info(
            "DUP(unique): 既存レコードにつき挿入スキップ | "
            f"DB={DBNAME}, table={TABLENAME}, user={user_name}, key={norm_key}, "
            f"dt={datetime_value}, url={media_url}, sql={last_sql}, params={last_params}"
        )
        return False

    except sqlite3.Error as e:
        # その他のDBエラーはロールバックしてフルログ
        error_msg = (
            f"データベースエラーが発生しました: {e}; "
            f"DB='{DBNAME}', table='{TABLENAME}', "
            f"user='{user_name}', key='{norm_key}', dt='{datetime_value}', url='{media_url}', "
            f"sql='{last_sql}', params={last_params}"
        )
        logger.error(error_msg)
        logger.error("Traceback:\n" + traceback.format_exc())
        print(error_msg)
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()


### メディアダウンロード ###
def download_media(logger, url, username, type):
    try:
        user_dir = os.path.join("media", username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            print(f"フォルダを作成しました: {user_dir}")

        # ファイル名を生成（ユーザー名フォルダ配下）
        time.sleep(2)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = os.path.join(user_dir, f"{username}_{timestamp}.{type}")

        # 動画のダウンロード
        print(f"ダウンロードを開始します: {filename}")
        logger.info(f"ダウンロードを開始します: {filename}")
        response = requests.get(url)
        response.raise_for_status()

        # ファイルとして保存
        with open(filename, "wb") as f:
            f.write(response.content)

        print(f"ダウンロード完了: {filename}")
        logger.info(f"ダウンロード完了: {filename}")

        if type == "jpg":
            extend_image_to_size(logger, filename)

        return True

    except Exception as e:
        print(f"メディアダウンロードでエラーが発生しました: {str(e)}")
        logger.error(f"メディアダウンロードでエラーが発生しました: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)
        return False


### 画像リサイズ ###
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

        if img.mode != "RGB":
            img = img.convert("RGB")

        current_width, current_height = img.size

        if logger:
            logger.info(f"元の画像サイズ: {current_width}x{current_height}")

        new_width = max(current_width, target_width)
        new_height = max(current_height, target_height)

        if new_width > current_width or new_height > current_height:
            try:
                new_img = Image.new("RGB", (new_width, new_height), "black")
                x = (new_width - current_width) // 2
                y = (new_height - current_height) // 2
                new_img.paste(img, (x, y))

                # 保存
                new_img.save(output_path, "JPEG", quality=95)
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
                img.save(output_path, "JPEG", quality=95)
            return False

    except Exception as e:
        if logger:
            logger.error(f"画像処理中にエラーが発生: {str(e)}")
        raise


### メディア確認 ###
def check_media(username):
    media_dir = os.path.join("media", username)

    # ディレクトリが存在しない場合はNoneを返す
    if not os.path.exists(media_dir) or not os.path.isdir(media_dir):
        return None

    # ディレクトリ内のファイル一覧を取得
    files = os.listdir(media_dir)

    # ファイルが1つもない場合はNoneを返す
    if not files:
        return None

    # 最初のファイルのフルパスを返す
    return os.path.join(media_dir, files[0])


### 説明文取得_動画 ###
def get_video_description(video_path):
    """動画から0秒時点で表示されているテキストを上から順に抽出する関数"""
    credentials_path = os.path.join("service_account", "g-link-meo-e7d409a75ece.json")

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        video_client = videointelligence.VideoIntelligenceServiceClient(credentials=credentials)

        features = [videointelligence.Feature.TEXT_DETECTION]
        video_context = videointelligence.VideoContext()

        with io.open(video_path, "rb") as file:
            input_content = file.read()

        operation = video_client.annotate_video(
            request={
                "features": features,
                "input_content": input_content,
                "video_context": video_context,
            }
        )

        result = operation.result(timeout=300)
        annotation_result = result.annotation_results[0]

        if not hasattr(annotation_result, "text_annotations") or not annotation_result.text_annotations:
            return None

        # 0秒時点のテキストと位置情報を収集
        initial_texts = []
        for text_annotation in annotation_result.text_annotations:
            start_time = text_annotation.segments[0].segment.start_time_offset.seconds
            if start_time == 0:
                y_position = (
                    sum(vertex.y for vertex in text_annotation.segments[0].frames[0].rotated_bounding_box.vertices) / 4
                )
                initial_texts.append({"text": text_annotation.text, "y_position": y_position})

        # y座標で昇順にソート（上から下）
        initial_texts.sort(key=lambda x: x["y_position"])

        # テキストを改行区切りの文字列として結合
        return "\n".join(item["text"] for item in initial_texts) if initial_texts else None

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None


### 説明文整形_GPT ###
def format_description_GPT(text, username, logger):
    """テキストを整形する関数"""
    if username in text:
        logger.info(f"応答に{username}が含まれています")
        return ""

    api_key = os.getenv("OPENAI_API_KEY")

    system_prompt = "与えられたテキストを指定された規則に従って整形します。"
    user_prompt = """
    下記の条件でテキストを整形して、整形したテキストのみを回答してください。
    ・UserIDなどの文章上意味のない文字列を除去してください。
    ・意味のある単語または文章が存在しない場合は、「None」と回答してください。
    ・文章が存在する場合は、意味が通じる自然な文章に整形してください。
    ・オリジナルのテキストは生成しないでください。
    """

    try:
        # OpenAI クライアントの初期化
        client = OpenAI(api_key=api_key)

        # メッセージの作成と送信
        response = client.chat.completions.create(
            model="gpt-4o",  # 推奨モデル
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{user_prompt}\n\n入力テキスト：{text}",
                        }
                    ],
                },
            ],
            max_tokens=500,
        )

        # レスポンスの処理
        if not response.choices:
            logger.info("応答内容がありません")
            return None

        response_text = response.choices[0].message.content

        if "None" in response_text:
            logger.info("応答に'None'が含まれています")
            return None

        return response_text

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return None


### 説明文整形_Claude（現在未使用） ###
def format_description_Claude(text, username, logger):
    if username in text:
        logger.info(f"応答に{username}が含まれています")
        return ""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    prompt = """
    下記の条件で文章を整形して、整形した文章のみを回答してください。
    ・UserIDなどの文章上意味のない文字列を除去してください。
    ・意味のある単語または文章が存在しない場合は、「None」と回答してください。
    ・文章が存在する場合は、意味が通じる自然な文章に整形してください。
    ・オリジナルの文言は生成しないでください。
    """

    try:
        client = Anthropic(api_key=api_key)

        # メッセージの作成と送信
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "text", "text": text},
                    ],
                }
            ],
        )

        # レスポンスの処理
        if not message.content:
            print("応答内容がありません")
            return None

        # content は配列なので、最初の要素のテキストを取得
        response_text = message.content[0].text

        if "None" in response_text:
            print("応答に'None'が含まれています")
            return None

        return response_text

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None


### 説明文取得_画像_GPT ###
def get_image_description_GPT(image_path, logger):
    """画像からテキストを抽出する関数"""
    api_key = os.getenv("OPENAI_API_KEY")

    system_prompt = "与えられた画像からテキストを抽出します。"
    user_prompt = """
    Instagramのストーリー投稿の画像を添付するので、編集によって追加されたテキストを抽出し、そのテキストのみを回答してください。
    編集によって追加されたテキストが存在しない場合は「None」と回答してください。
    上記以外の内容は回答しないでください。
    """

    try:
        # OpenAI クライアントの初期化
        client = OpenAI(api_key=api_key)

        # 画像のエンコード
        base64_image = encode_image(image_path)

        # メッセージの作成と送信
        response = client.chat.completions.create(
            model="gpt-4o",  # 最新のOCR対応モデル
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                },
            ],
            max_tokens=500,
        )

        # レスポンスの処理
        if not response.choices:
            print("応答内容がありません")
            return None

        response_text = response.choices[0].message.content

        if "None" in response_text:
            logger.info("応答に'None'が含まれています")
            return None

        return response_text

    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return None


### 説明文取得_画像_Claude（現在未使用） ###
def get_image_description_Claude(image_path, logger):
    """画像からテキストを抽出する関数"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    prompt = """
    Instagramの投稿文を生成します。
    画像内のテキストを抽出し、下記の条件で文章を生成して、生成した文章のみを回答してください。
    ・UserIDなどの文章上意味のない文字列を除去してください。
    ・意味のある単語または文章が存在しない場合は、「None」と回答してください。
    ・文章が存在する場合は、意味が通じる自然な文章に整形してください。
    ・オリジナルの文言は生成しないでください。
    """

    try:
        # クライアントの初期化
        client = Anthropic(api_key=api_key)

        # 画像のエンコード
        base64_image = encode_image(image_path)

        # メッセージの作成と送信
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image,
                            },
                        },
                    ],
                }
            ],
        )

        # レスポンスの処理
        if not message.content:
            print("応答内容がありません")
            return None

        # content は配列なので、最初の要素のテキストを取得
        response_text = message.content[0].text

        if "None" in response_text:
            logger.info("応答に'None'が含まれています")
            return None

        return response_text

    except Exception as e:
        logger.info(f"エラーが発生しました: {str(e)}")
        return None


### 画像エンコード ###
def encode_image(image_path):
    """画像をbase64エンコードする関数"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


### 説明文_手動整形  ###
def clean_description(text, USERNAME, logger):
    remove_list = ["続きを読む", USERNAME]

    try:
        # 入力チェック
        if text is None:
            return ""

        # 文字列に変換
        text = str(text)
        result = text

        # 文字の除去
        for char in remove_list:
            if char in result:
                # @{USERNAME}の形式の場合は除去しない
                if char == USERNAME and f"@{USERNAME}" in result:
                    continue

                logger.info(f"応答に{char}が含まれています")
                return ""

        return result

    except Exception as e:
        print(f"Error in clean_description: {e}")
        return text  # エラー時は元の文字列を返す

### datetime属性の抽出 ###
def extract_datetime(driver, logger, timeout=10):
    """
    ストーリーの<time>タグからdatetime属性を抽出する。
    """
    try:
        logger.info("datetime属性の抽出を開始します")
        time_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//time[@datetime]"))
        )
        datetime_value = time_element.get_attribute("datetime")
        logger.info(f"抽出されたdatetime: {datetime_value}")
        return datetime_value
    except Exception as e:
        logger.warning(f"datetimeの抽出に失敗しました: {str(e)}")
        return None


########## メイン　##########
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

        time.sleep(10)

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
        return 3

    ########## プロフィール写真をクリック(ストーリーチェック) ##########
    try:
        xpath = f"//img[contains(@alt, '{USERNAME}のプロフィール写真')]"
        profile_image = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        profile_image.click()
        logger.info("プロフィール写真のクリックに成功しました")

    except Exception as e:
        error_msg = f"プロフィール画像のクリックに失敗しました: {e}"
        logger.error(error_msg)
        print(error_msg)
        driver.quit()
        return 1

    ########## メディア取得 ##########
    # 1.動画取得
    # 2.なければ画像取得
    # 3.なければ
    try:
        # video_check = driver.find_elements(
        #    By.XPATH,
        #    "//div[contains(@class, 'x10l6tqk')][@data-visualcompletion='ignore']"
        # )

        # 動画要素を待つ
        wait = WebDriverWait(driver, 3)
        video_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "video")))

        if video_element:
            logger.info(f"{USERNAME}: 動画を検出しました")

            # datetime抽出を試みる
            datetime_value = extract_datetime(driver, logger)
            if datetime_value:
                logger.info(f"{USERNAME} の投稿日時: {datetime_value}")

            # 動画のsrcを取得
            video_src = video_element.get_attribute("src")
            # 動画をローカルに保存
            print(video_src)

            # driver.quit()
            # urls = get_video_urls(driver)

            time.sleep(1)
            # ネットワーク取得
            netlog = driver.get_log("performance")
            # url(部分的)取得
            urls = extract_request_urls_v2(netlog)
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

                result_blob = checkRecord(USERNAME, cache_key, url, logger, datetime_value)

            if result_blob:
                # 動画DL
                download_media(logger, url, USERNAME, "mp4")
            else:
                driver.quit()
                return 1

            driver.quit()
            logger.info("処理終了")
            return 0

    except Exception as e:
        # error_msg = f"動画の取得に失敗しました: {e}"
        error_msg = f"動画の取得に失敗しました"
        logger.info(error_msg)
        print(error_msg)
        datetime_value = extract_datetime(driver, logger)
        try:
            # 画像要素の取得
            target_classes = [
                "xl1xv1r",
                "x5yr21d",
                "xmz0i5r",
                "x193iq5w",
                "xh8yej3",
            ]
            class_condition = " and ".join([f"contains(@class, '{cls}')" for cls in target_classes])
            xpath = f"//img[{class_condition} and contains(@alt, 'Photo by')]"

            image_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
            image_url = image_element.get_attribute("src")

            result = False
            if image_url:
                logger.info("画像URLを取得しました")
                cache_key = getkey(image_url)
                result = checkRecord(USERNAME, cache_key, image_url, logger, datetime_value)

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
            # error_msg = f"画像の取得に失敗しました: {e}"
            error_msg = "画像の取得に失敗しました"
            logger.info(error_msg)
            print(error_msg)
            driver.quit()
            logger.info("処理終了")
            return 1

    finally:
        ### 説明文取得 ###
        filepath = check_media(USERNAME)
        description = None
        if filepath:
            print(f"ファイルパス: {filepath}")

            # ディレクトリパスを構築
            description_dir = os.path.join("media", USERNAME, "description")
            if not os.path.exists(description_dir):
                os.makedirs(description_dir)

            # 一時ファイルのパス（プロセスIDを含む）
            temp_file_path = os.path.join(description_dir, f"{process_id}.txt")

            # メディア種別取得
            file_extension = filepath.lower().split(".")[-1]

            # 動画
            # if file_extension in ["mp4", "mov", "avi", "wmv", "flv", "mkv"]:
            #     description = get_video_description(filepath)
            #     logger.info(f"説明文: {description}")
                # description = format_description_GPT(description, USERNAME, logger)

            # 画像
            # else:
                # description = get_image_description_GPT(filepath, logger)

            logger.info(f"説明文_AI: {description}")

            description = clean_description(description, USERNAME, logger)
            logger.info(f"説明文_最終: {description}")

            # データを一時ファイルに書き込み
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(description)


if __name__ == "__main__":
    result = main()
    sys.exit(result)
