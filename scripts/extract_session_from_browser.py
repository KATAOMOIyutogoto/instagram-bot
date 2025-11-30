"""
ブラウザでInstagramにログインして、セッション情報を自動取得するツール

使用方法:
    python scripts/extract_session_from_browser.py <セッションファイル>

例:
    python scripts/extract_session_from_browser.py data/session_account1.json
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

# 既存のupdate_session_from_browser関数をインポート
from scripts.update_session_from_browser import update_session_from_browser


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


def main():
    """メイン関数"""
    print("=" * 60)
    print("Instagram セッション情報自動取得ツール")
    print("=" * 60)
    print()

    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <セッションファイル>")
        print()
        print("例:")
        print(f'  python {sys.argv[0]} data/session_account1.json')
        print()
        print("説明:")
        print("  このツールはブラウザを自動的に開き、Instagramのログインページを表示します。")
        print("  手動でログインすると、セッション情報を自動的に取得して保存します。")
        sys.exit(1)

    session_file = sys.argv[1]
    
    # セッションファイルのディレクトリが存在することを確認
    session_path = Path(session_file)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    if not SELENIUM_AVAILABLE:
        print("[ERROR] Seleniumライブラリが使用できません")
        sys.exit(1)

    # ブラウザを起動
    print("[INFO] ブラウザを起動しています...")
    driver = get_chrome_driver()
    
    if not driver:
        print("[ERROR] ブラウザの起動に失敗しました")
        sys.exit(1)

    try:
        # Instagramのログインページに移動
        print("[INFO] Instagramのログインページを開いています...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)

        # ログインを待つ
        if not wait_for_login(driver, timeout=300):
            print("\n[ERROR] ログインが完了しませんでした")
            print("[INFO] ブラウザを確認して、ログインが完了しているか確認してください")
            input("\n[INFO] 何かキーを押してブラウザを閉じます...")
            driver.quit()
            sys.exit(1)

        # セッション情報を取得
        print("\n[INFO] セッション情報を取得しています...")
        sessionid, ds_user_id = extract_session_from_cookies(driver)

        if not sessionid:
            print("[ERROR] セッション情報の取得に失敗しました")
            input("\n[INFO] 何かキーを押してブラウザを閉じます...")
            driver.quit()
            sys.exit(1)

        # セッションファイルを保存
        print("\n[INFO] セッションファイルを保存しています...")
        success = update_session_from_browser(session_file, sessionid, ds_user_id)

        if success:
            print("\n" + "=" * 60)
            print("[OK] セッション情報の取得と保存が完了しました！")
            print("=" * 60)
            print()
            print("次のステップ:")
            print("  1. Botを実行してセッション情報が有効か確認")
            print(f"     python scripts/check_all_accounts_login.py")
            print()
            print("  2. 有効な場合は、そのまま使用できます")
            print("=" * 60)
        else:
            print("\n[ERROR] セッションファイルの保存に失敗しました")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[INFO] ユーザーによって中断されました")
    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ブラウザを閉じるかどうか確認
        print("\n" + "=" * 60)
        response = input("ブラウザを閉じますか？ (y/N): ").strip().lower()
        if response == 'y' or response == 'yes':
            driver.quit()
            print("[INFO] ブラウザを閉じました")
        else:
            print("[INFO] ブラウザは開いたままにします")
            print("       （手動で閉じてください）")


if __name__ == "__main__":
    main()

