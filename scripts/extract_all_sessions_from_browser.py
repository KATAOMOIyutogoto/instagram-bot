"""
config.jsonにある全てのアカウントのセッション情報を自動取得するツール

使用方法:
    python scripts/extract_all_sessions_from_browser.py

このツールは:
1. config.jsonから全てのアカウントを読み込み
2. 各アカウントに対して順番にブラウザでログイン
3. セッション情報を自動取得して保存
"""

import json
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
    import undetected_chromedriver as uc

    SELENIUM_AVAILABLE = True
except ImportError as e:
    SELENIUM_AVAILABLE = False
    error_msg = str(e)
    
    # distutils関連のエラーの場合は特別なメッセージを表示
    if "distutils" in error_msg.lower() or "No module named 'distutils'" in error_msg:
        print(f"[ERROR] distutilsモジュールが見つかりません: {e}")
        print("Python 3.12以降ではdistutilsが削除されているため、setuptoolsが必要です。")
        print("以下のコマンドでインストールしてください:")
        print("pip install setuptools")
        print()
        print("その後、再度以下のコマンドを実行してください:")
        print("pip install -r requirements.txt")
    else:
        print(f"[ERROR] Seleniumライブラリがインストールされていません: {e}")
        print("以下のコマンドでインストールしてください:")
        print("pip install -r requirements.txt")
    sys.exit(1)

# 既存の関数をインポート
from scripts.update_session_from_browser import update_session_from_browser

# extract_session_from_browser.pyから関数をコピー（インポートできないため）
def get_chrome_driver():
    """Chromeドライバーを取得（既存のChromeプロセスを終了せずに開く）"""
    try:
        # undetected_chromedriverを使用（検出回避、推奨）
        try:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            
            driver = uc.Chrome(options=chrome_options)
            print("[OK] undetected_chromedriverを使用してブラウザを起動しました")
            return driver
        except Exception as uc_error:
            print(f"[WARNING] undetected_chromedriverでの起動に失敗: {uc_error}")
            print("[INFO] 通常のChromeDriverで試行します...")
            
            # フォールバック: 通常のChromeDriver（互換性のためシンプルなオプションのみ）
            chrome_options_fallback = Options()
            chrome_options_fallback.add_argument("--start-maximized")
            chrome_options_fallback.add_argument("--disable-blink-features=AutomationControlled")
            # excludeSwitchesは通常のChromeDriverでは認識されない場合があるため削除
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options_fallback)
            print("[OK] ChromeDriverを使用してブラウザを起動しました")
            return driver

    except Exception as e:
        print(f"[ERROR] Chromeドライバーの起動に失敗しました: {e}")
        print("[INFO] Chromeがインストールされているか確認してください")
        import traceback
        traceback.print_exc()
        return None


def wait_for_login(driver, timeout=300):
    """
    Instagramにログインするのを待つ
    
    Args:
        driver: WebDriverインスタンス
        timeout: タイムアウト時間（秒）
    
    Returns:
        bool: ログインが成功したかどうか
    """
    print("\n" + "=" * 60)
    print("Instagramにログインしてください")
    print("=" * 60)
    print()
    print("手順:")
    print("  1. ブラウザでInstagramのログインページが開きます")
    print("  2. ユーザー名とパスワードを入力してログインしてください")
    print("  3. チャレンジ認証がある場合は完了してください")
    print("  4. ログインが完了すると、自動的にセッション情報を取得します（通常は数秒以内）")
    print()
    print(f"最大待機時間: {timeout}秒（{timeout // 60}分）")
    print("=" * 60)
    print()

    start_time = time.time()
    last_url = ""
    check_count = 0

    while time.time() - start_time < timeout:
        try:
            # Cookieを直接チェック（最も確実で速い方法）
            cookies = driver.get_cookies()
            has_sessionid = any(cookie.get("name") == "sessionid" for cookie in cookies)
            
            if has_sessionid:
                # sessionidが存在する場合はログイン済みの可能性が高い
                current_url = driver.current_url
                # ログインページにいないことを確認
                if "/accounts/login" not in current_url and "/accounts/onetap" not in current_url:
                    print("\n[OK] ログインが検出されました！（Cookie確認）")
                    time.sleep(1)  # 少し待ってからセッション情報を取得
                    return True
            
            current_url = driver.current_url
            
            # URLが変更された場合、ログ出力
            if current_url != last_url:
                print(f"[INFO] 現在のURL: {current_url}")
                last_url = current_url

            # Instagramのホームページに到達したかチェック
            if "instagram.com" in current_url:
                # ログインページから脱出したかチェック
                if "/accounts/login" not in current_url and "/accounts/onetap" not in current_url:
                    # ログイン済みのサインを確認
                    try:
                        # 検索バーやナビゲーションメニューが表示されているかチェック（非同期で高速化）
                        wait = WebDriverWait(driver, 2)
                        # ホームページの特徴的な要素を探す
                        wait.until(
                            EC.any_of(
                                EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="ホーム"]')),
                                EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Home"]')),
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="ホーム"]')),
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'svg[aria-label="Home"]')),
                            )
                        )
                        print("\n[OK] ログインが検出されました！（ページ要素確認）")
                        time.sleep(1)  # 少し待ってからセッション情報を取得
                        return True
                    except:
                        # まだログインしていない可能性がある
                        pass

            # 1秒ごとにチェック（より頻繁にチェックして速く検出）
            time.sleep(1)
            check_count += 1
            
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and check_count % 10 == 0:  # 10秒ごとに進捗を表示
                print(f"[INFO] 待機中... ({elapsed}秒経過) - ログイン完了をお待ちください...")

        except Exception as e:
            # ドライバーが閉じられた場合など
            if "invalid session id" in str(e).lower() or "no such window" in str(e).lower():
                print("\n[ERROR] ブラウザが閉じられました")
                return False
            time.sleep(1)

    print(f"\n[ERROR] タイムアウトしました（{timeout}秒）")
    return False


def extract_session_from_cookies(driver):
    """
    ブラウザのCookieからセッション情報を抽出
    
    Args:
        driver: WebDriverインスタンス
    
    Returns:
        tuple: (sessionid, ds_user_id) または (None, None)
    """
    try:
        cookies = driver.get_cookies()
        sessionid = None
        ds_user_id = None

        for cookie in cookies:
            if cookie["name"] == "sessionid":
                sessionid = cookie["value"]
                print(f"[OK] sessionidを取得しました: {sessionid[:50]}...")
            elif cookie["name"] == "ds_user_id":
                ds_user_id = cookie["value"]
                print(f"[OK] ds_user_idを取得しました: {ds_user_id}")

        if sessionid:
            return sessionid, ds_user_id
        else:
            print("[ERROR] sessionidが見つかりませんでした")
            return None, None

    except Exception as e:
        print(f"[ERROR] Cookieの取得に失敗しました: {e}")
        return None, None


def load_config(config_path: str = "config/config.json") -> dict:
    """設定ファイルを読み込む"""
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"[ERROR] 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] 設定ファイルのJSON解析エラー: {e}")
        sys.exit(1)


def get_all_accounts(config: dict) -> list[dict]:
    """
    config.jsonから全てのアカウントを取得
    
    Args:
        config: 設定ファイルの内容
    
    Returns:
        アカウント情報のリスト
    """
    accounts = []
    
    # instagram_accounts 配列から取得
    instagram_accounts = config.get("instagram_accounts", [])
    
    for account in instagram_accounts:
        # enabledがFalseのアカウントはスキップ
        if account.get("enabled", True) is False:
            print(f"[INFO] アカウント {account.get('username', 'unknown')} は無効化されているためスキップします")
            continue
        
        username = account.get("username")
        session_file = account.get("session_file")
        
        if not username or not session_file:
            print(f"[WARNING] アカウント情報が不完全です: {account}")
            continue
        
        accounts.append({
            "username": username,
            "password": account.get("password", ""),  # パスワードは参考情報のみ（実際には使用しない）
            "session_file": session_file,
        })
    
    # 旧形式のinstagram設定もチェック
    instagram_config = config.get("instagram", {})
    if instagram_config:
        username = instagram_config.get("username")
        session_file = instagram_config.get("session_file")
        if username and session_file:
            # 既にリストに含まれていないかチェック
            if not any(acc["session_file"] == session_file for acc in accounts):
                accounts.append({
                    "username": username,
                    "password": instagram_config.get("password", ""),
                    "session_file": session_file,
                })
    
    return accounts


def extract_session_for_account(account: dict, account_num: int, total_accounts: int) -> bool:
    """
    1つのアカウントのセッション情報を取得
    
    Args:
        account: アカウント情報の辞書
        account_num: 現在のアカウント番号（1から開始）
        total_accounts: 全アカウント数
    
    Returns:
        成功したかどうか
    """
    username = account["username"]
    session_file = account["session_file"]
    
    print("\n" + "=" * 70)
    print(f"アカウント {account_num}/{total_accounts}: {username}")
    print("=" * 70)
    print(f"セッションファイル: {session_file}")
    print()
    
    # セッションファイルのディレクトリが存在することを確認
    session_path = Path(session_file)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ブラウザを起動
    print("[INFO] ブラウザを起動しています...")
    driver = get_chrome_driver()
    
    if not driver:
        print("[ERROR] ブラウザの起動に失敗しました")
        return False
    
    try:
        # Instagramのログインページに移動
        print("[INFO] Instagramのログインページを開いています...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)
        
        print(f"\n[INFO] アカウント '{username}' でログインしてください")
        
        # ログインを待つ（タイムアウト5分）
        if not wait_for_login(driver, timeout=300):
            print("\n[ERROR] ログインが完了しませんでした")
            print(f"[INFO] アカウント '{username}' のログインをスキップします")
            return False
        
        # セッション情報を取得
        print("\n[INFO] セッション情報を取得しています...")
        sessionid, ds_user_id = extract_session_from_cookies(driver)
        
        if not sessionid:
            print("[ERROR] セッション情報の取得に失敗しました")
            return False
        
        # セッションファイルを保存
        print("\n[INFO] セッションファイルを保存しています...")
        success = update_session_from_browser(session_file, sessionid, ds_user_id)
        
        if success:
            print(f"[OK] アカウント '{username}' のセッション情報を取得しました！")
            return True
        else:
            print(f"[ERROR] アカウント '{username}' のセッションファイルの保存に失敗しました")
            return False
    
    except KeyboardInterrupt:
        print("\n\n[INFO] ユーザーによって中断されました")
        raise
    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # ブラウザを閉じる
        try:
            driver.quit()
            print("[INFO] ブラウザを閉じました")
        except:
            pass


def main():
    """メイン関数"""
    print("=" * 70)
    print("Instagram 全アカウント セッション情報自動取得ツール")
    print("=" * 70)
    print()
    
    if not SELENIUM_AVAILABLE:
        print("[ERROR] Seleniumライブラリが使用できません")
        sys.exit(1)
    
    # 設定ファイルを読み込み
    print("[INFO] 設定ファイルを読み込んでいます...")
    config = load_config("config/config.json")
    
    # 全アカウントを取得
    accounts = get_all_accounts(config)
    
    if not accounts:
        print("[ERROR] 取得可能なアカウントが見つかりませんでした")
        print("[INFO] config.json に instagram_accounts が設定されているか確認してください")
        sys.exit(1)
    
    print(f"[INFO] {len(accounts)} 個のアカウントが見つかりました:")
    for idx, account in enumerate(accounts, 1):
        print(f"  {idx}. {account['username']} -> {account['session_file']}")
    
    print()
    print("=" * 70)
    print("注意事項:")
    print("  - 各アカウントに対してブラウザでログインする必要があります")
    print("  - チャレンジ認証がある場合は完了してください")
    print("  - 1つのアカウントが完了すると、次のアカウントの処理が始まります")
    print("  - 途中で中断する場合は Ctrl+C を押してください")
    print("=" * 70)
    print()
    
    response = input("続行しますか？ (y/N): ").strip().lower()
    if response != 'y' and response != 'yes':
        print("[INFO] 処理をキャンセルしました")
        sys.exit(0)
    
    # 各アカウントに対して処理を実行
    success_count = 0
    failed_count = 0
    failed_accounts = []
    
    for idx, account in enumerate(accounts, 1):
        try:
            success = extract_session_for_account(account, idx, len(accounts))
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                failed_accounts.append(account["username"])
            
            # 最後のアカウントでない場合、次のアカウントに移る前に少し待機
            if idx < len(accounts):
                print("\n" + "=" * 70)
                print(f"次のアカウントの準備中...")
                print("=" * 70)
                time.sleep(2)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 70)
            print("[INFO] ユーザーによって処理が中断されました")
            print("=" * 70)
            break
    
    # 結果サマリーを表示
    print("\n" + "=" * 70)
    print("処理結果サマリー")
    print("=" * 70)
    print(f"成功: {success_count} アカウント")
    print(f"失敗: {failed_count} アカウント")
    
    if failed_accounts:
        print("\n失敗したアカウント:")
        for username in failed_accounts:
            print(f"  - {username}")
    
    print()
    print("=" * 70)
    print("次のステップ:")
    print("  1. Botを実行してセッション情報が有効か確認")
    print("     python scripts/check_all_accounts_login.py")
    print()
    print("  2. 有効な場合は、そのまま使用できます")
    print("=" * 70)
    
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

