"""
特定のアカウントのログイン状態を確認し、セッションが無効な場合はパスワードでログインを試みるスクリプト
"""
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from instagrapi import Client
    from instagrapi.exceptions import ChallengeRequired, LoginRequired, TwoFactorRequired
except ImportError:
    print("[ERROR] instagrapiがインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install instagrapi")
    sys.exit(1)

import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger("instagrapi").setLevel(logging.ERROR)
logging.getLogger("private_request").setLevel(logging.ERROR)
logging.getLogger("public_request").setLevel(logging.ERROR)


def check_and_login(username: str, password: str, session_file: str) -> dict:
    """
    アカウントのログイン状態を確認し、セッションが無効な場合はパスワードでログインを試みる
    
    Args:
        username: Instagramユーザー名
        password: パスワード
        session_file: セッションファイルのパス
        
    Returns:
        結果の辞書
    """
    result = {
        "username": username,
        "session_file": session_file,
        "status": "unknown",
        "message": "",
    }
    
    client = Client()
    session_path = Path(session_file)
    
    # セッションファイルが存在する場合は読み込んで確認
    if session_path.exists():
        try:
            client.load_settings(str(session_path))
            # セッションが有効か確認
            try:
                client.account_info()
                result["status"] = "success"
                result["message"] = "セッションファイルが有効です。ログイン成功"
                return result
            except LoginRequired:
                result["status"] = "session_invalid"
                result["message"] = "セッションが無効です。パスワードでログインを試みます..."
            except Exception as e:
                error_msg = str(e)
                if "user_has_logged_out" in error_msg:
                    result["status"] = "session_invalid"
                    result["message"] = "セッションが無効です（ログアウト済み）。パスワードでログインを試みます..."
                else:
                    result["status"] = "session_invalid"
                    result["message"] = f"セッションエラー: {error_msg}。パスワードでログインを試みます..."
        except Exception as e:
            result["status"] = "session_invalid"
            result["message"] = f"セッションファイルの読み込みエラー: {e}。パスワードでログインを試みます..."
    else:
        result["status"] = "no_session"
        result["message"] = "セッションファイルが存在しません。パスワードでログインを試みます..."
    
    # パスワードでログインを試みる
    print(f"パスワードでログインを試みます: {username}")
    try:
        client = Client()  # 新しいクライアントインスタンス
        client.login(username, password)
        
        # セッションファイルを保存
        session_path.parent.mkdir(parents=True, exist_ok=True)
        client.dump_settings(str(session_path))
        
        # ログイン成功を確認
        account_info = client.account_info()
        result["status"] = "login_success"
        result["message"] = f"パスワードログイン成功！セッションファイルを更新しました。ユーザー名: {account_info.username}"
        return result
        
    except TwoFactorRequired:
        result["status"] = "two_factor_required"
        result["message"] = "2FA認証が必要です。手動でログインしてください。"
        return result
    except ChallengeRequired:
        result["status"] = "challenge_required"
        result["message"] = "チャレンジ認証が必要です。手動でログインしてください。"
        return result
    except Exception as e:
        error_msg = str(e)
        if "blacklist" in error_msg.lower() or "ip address" in error_msg.lower():
            result["status"] = "ip_blacklisted"
            result["message"] = f"IPアドレスがブラックリストに登録されています: {error_msg}"
        else:
            result["status"] = "login_failed"
            result["message"] = f"ログイン失敗: {error_msg}"
        return result


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <アカウント名>")
        print()
        print("例:")
        print(f"  python {sys.argv[0]} g_l_2026_5")
        sys.exit(1)
    
    account_username = sys.argv[1]
    
    # config.jsonからアカウント情報を取得
    config_path = Path("config/config.json")
    if not config_path.exists():
        print(f"[ERROR] 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    accounts = config.get("instagram_accounts", [])
    account = None
    for acc in accounts:
        if acc.get("username") == account_username:
            account = acc
            break
    
    if not account:
        print(f"[ERROR] アカウント '{account_username}' が見つかりません")
        sys.exit(1)
    
    username = account.get("username")
    password = account.get("password")
    session_file = account.get("session_file")
    
    if not password:
        print(f"[ERROR] アカウント '{username}' のパスワードが設定されていません")
        sys.exit(1)
    
    if not session_file:
        print(f"[ERROR] アカウント '{username}' のセッションファイルが設定されていません")
        sys.exit(1)
    
    print("=" * 60)
    print(f"アカウントログイン確認・再ログイン: {username}")
    print("=" * 60)
    print()
    
    result = check_and_login(username, password, session_file)
    
    print(f"状態: {result['status']}")
    print(f"メッセージ: {result['message']}")
    print()
    
    if result["status"] == "success":
        print("[OK] セッションファイルが有効です。ログイン不要")
        sys.exit(0)
    elif result["status"] == "login_success":
        print("[OK] パスワードログインに成功しました。セッションファイルを更新しました。")
        sys.exit(0)
    else:
        print(f"[ERROR] {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()

