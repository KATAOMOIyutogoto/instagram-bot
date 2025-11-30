"""
すべてのInstagramアカウントのログイン状態を確認するスクリプト
セッションファイルを読み込んで、各アカウントがログインできるかチェック
"""

import json
import sys
import os
from pathlib import Path

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

# ログレベルをWARNINGに設定（INFOメッセージを抑制）
logging.basicConfig(level=logging.WARNING)
logging.getLogger("instagrapi").setLevel(logging.ERROR)
logging.getLogger("private_request").setLevel(logging.ERROR)
logging.getLogger("public_request").setLevel(logging.ERROR)


def check_account_login(username: str, session_file: str) -> dict:
    """
    アカウントのログイン状態を確認

    Args:
        username: Instagramユーザー名
        session_file: セッションファイルのパス

    Returns:
        確認結果の辞書
    """
    result = {
        "username": username,
        "session_file": session_file,
        "session_exists": False,
        "login_status": "unknown",
        "message": "",
        "account_info": None,
    }

    session_path = Path(session_file)

    # セッションファイルの存在確認
    if not session_path.exists():
        result["login_status"] = "no_session"
        result["message"] = "セッションファイルが存在しません"
        return result

    result["session_exists"] = True

    try:
        # Clientインスタンスを作成
        client = Client()

        # セッションファイルを読み込み
        try:
            client.load_settings(str(session_path))
        except Exception as e:
            result["login_status"] = "invalid_session"
            result["message"] = f"セッションファイルの読み込みに失敗: {e}"
            return result

        # アカウント情報を取得してログイン状態を確認
        try:
            account_info = client.account_info()
            result["login_status"] = "logged_in"
            result["message"] = "ログイン成功"
            # 属性を安全に取得（存在しない場合はNone）
            result["account_info"] = {
                "pk": getattr(account_info, "pk", None),
                "username": getattr(account_info, "username", None),
                "full_name": getattr(account_info, "full_name", None),
                "is_verified": getattr(account_info, "is_verified", None),
                "media_count": getattr(account_info, "media_count", None),
                "follower_count": getattr(account_info, "follower_count", None),
            }
            return result
        except LoginRequired:
            result["login_status"] = "login_required"
            result["message"] = "ログインが必要です（セッションが無効）"
            return result
        except ChallengeRequired:
            result["login_status"] = "challenge_required"
            result["message"] = "チャレンジ認証が必要です"
            return result
        except Exception as e:
            error_str = str(e).lower()
            if "blacklist" in error_str or "ip address" in error_str:
                result["login_status"] = "ip_blacklisted"
                result["message"] = f"IPアドレスがブラックリストに追加されています: {str(e)[:100]}"
            elif "challenge" in error_str:
                result["login_status"] = "challenge_required"
                result["message"] = "チャレンジ認証が必要です"
            else:
                result["login_status"] = "error"
                result["message"] = f"エラー: {str(e)[:100]}"
            return result

    except Exception as e:
        result["login_status"] = "error"
        result["message"] = f"予期しないエラー: {str(e)[:100]}"
        return result


def extract_user_id_from_sessionid(sessionid: str) -> str | None:
    """セッションIDからユーザーIDを抽出"""
    try:
        if "%3A" in sessionid:
            return sessionid.split("%3A")[0]
        elif ":" in sessionid:
            return sessionid.split(":")[0]
        return None
    except:
        return None


def check_session_duplicates(accounts: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """
    セッションIDの重複をチェック
    
    Args:
        accounts: アカウント設定のリスト
        
    Returns:
        ユーザーID -> [(username, session_file), ...] のマッピング（重複があるもののみ）
    """
    user_id_map: dict[str, list[tuple[str, str]]] = {}
    
    for account in accounts:
        username = account.get("username", "unknown")
        session_file = account.get("session_file", "")
        
        if not session_file:
            continue
        
        session_path = Path(session_file)
        if not session_path.exists():
            continue
        
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            auth_data = session_data.get("authorization_data", {})
            sessionid = auth_data.get("sessionid", "")
            ds_user_id = auth_data.get("ds_user_id", "")
            
            if not sessionid:
                continue
            
            # ユーザーIDを取得（ds_user_idがあればそれを使用、なければsessionidから抽出）
            user_id = ds_user_id if ds_user_id else extract_user_id_from_sessionid(sessionid)
            
            if user_id:
                if user_id not in user_id_map:
                    user_id_map[user_id] = []
                user_id_map[user_id].append((username, session_file))
        
        except Exception as e:
            continue
    
    # 重複があるもののみを返す
    duplicates = {user_id: accounts_list for user_id, accounts_list in user_id_map.items() if len(accounts_list) > 1}
    return duplicates


def check_all_accounts(config_path: str = "config/config.json") -> dict:
    """
    すべてのアカウントのログイン状態を確認

    Args:
        config_path: 設定ファイルのパス

    Returns:
        すべてのアカウントの確認結果
    """
    # 設定ファイルを読み込み
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] 設定ファイルの読み込みに失敗しました: {e}")
        sys.exit(1)

    # アカウントリストを取得
    accounts = config.get("instagram_accounts", [])
    if not accounts:
        print("[WARNING] instagram_accountsが設定されていません")
        accounts = []

    # セッションIDの重複をチェック
    duplicates = check_session_duplicates(accounts)
    
    # 重複しているアカウントを特定（2つ目以降を重複リストに追加）
    duplicate_accounts = set()
    if duplicates:
        print("=" * 60)
        print("⚠️ セッションID重複が検出されました")
        print("=" * 60)
        for user_id, accounts_list in duplicates.items():
            print(f"ユーザーID {user_id} が {len(accounts_list)} 個のアカウントで使用されています:")
            # 最初のアカウントは保持、2つ目以降を重複リストに追加
            for i, (username, session_file) in enumerate(accounts_list):
                if i == 0:
                    print(f"  - {username} ({session_file}) [最初のアカウント - このアカウントのみチェック]")
                else:
                    print(f"  - {username} ({session_file}) [重複 - ログインチェックをスキップ]")
                    duplicate_accounts.add((username, session_file))
        print()
        print("⚠️ 重複しているアカウントは、アカウント凍結を防ぐためログインチェックをスキップします")
        print()

    results = {
        "total_accounts": len(accounts),
        "checked_accounts": 0,
        "logged_in": 0,
        "login_required": 0,
        "challenge_required": 0,
        "ip_blacklisted": 0,
        "no_session": 0,
        "error": 0,
        "duplicate_skipped": 0,
        "accounts": [],
    }

    print("=" * 60)
    print("すべてのInstagramアカウントのログイン状態を確認中...")
    print("=" * 60)
    print(f"アカウント数: {len(accounts)}\n")

    # 各アカウントのログイン状態を確認
    for idx, account in enumerate(accounts, 1):
        username = account.get("username", "unknown")
        session_file = account.get("session_file", "")

        if not session_file:
            print(f"[{idx}/{len(accounts)}] {username}: セッションファイルが設定されていません")
            results["accounts"].append(
                {
                    "username": username,
                    "session_file": "",
                    "login_status": "no_config",
                    "message": "セッションファイルが設定されていません",
                }
            )
            results["no_session"] += 1
            continue

        # 重複しているアカウントの場合はスキップ
        if (username, session_file) in duplicate_accounts:
            print(f"[{idx}/{len(accounts)}] {username}: [SKIP] セッションID重複のためスキップ")
            results["accounts"].append(
                {
                    "username": username,
                    "session_file": session_file,
                    "login_status": "duplicate_skipped",
                    "message": "セッションID重複によりログインチェックをスキップ（アカウント凍結を防ぐため）",
                }
            )
            results["duplicate_skipped"] += 1
            continue

        print(f"[{idx}/{len(accounts)}] {username} を確認中...", end=" ")

        result = check_account_login(username, session_file)
        results["accounts"].append(result)
        results["checked_accounts"] += 1

        # ステータスに応じてカウントを更新
        if result["login_status"] == "logged_in":
            results["logged_in"] += 1
            print("[OK] ログイン成功")
        elif result["login_status"] == "login_required":
            results["login_required"] += 1
            print("[NG] ログインが必要")
        elif result["login_status"] == "challenge_required":
            results["challenge_required"] += 1
            print("[WARN] チャレンジ認証が必要")
        elif result["login_status"] == "ip_blacklisted":
            results["ip_blacklisted"] += 1
            print("[NG] IPアドレスがブラックリスト")
        elif result["login_status"] == "no_session":
            results["no_session"] += 1
            print("[NG] セッションファイルなし")
        else:
            results["error"] += 1
            print(f"[ERROR] {result['message']}")

    return results


def print_summary(results: dict):
    """結果のサマリーを表示"""
    print()
    print("=" * 60)
    print("確認結果サマリー")
    print("=" * 60)
    print(f"総アカウント数: {results['total_accounts']}")
    print(f"確認済み: {results['checked_accounts']}")
    print()
    print("ログイン状態:")
    print(f"  [OK] ログイン成功: {results['logged_in']}アカウント")
    print(f"  [NG] ログインが必要: {results['login_required']}アカウント")
    print(f"  [WARN] チャレンジ認証が必要: {results['challenge_required']}アカウント")
    print(f"  [NG] IPアドレスがブラックリスト: {results['ip_blacklisted']}アカウント")
    print(f"  [NG] セッションファイルなし: {results['no_session']}アカウント")
    print(f"  [SKIP] セッションID重複（スキップ）: {results.get('duplicate_skipped', 0)}アカウント")
    print(f"  [ERROR] エラー: {results['error']}アカウント")
    print()

    # 詳細情報を表示
    print("=" * 60)
    print("詳細情報")
    print("=" * 60)

    for account_result in results["accounts"]:
        username = account_result["username"]
        status = account_result["login_status"]
        message = account_result.get("message", "")

        if status == "logged_in":
            account_info = account_result.get("account_info", {})
            print(f"\n[OK] {username}: ログイン成功")
            if account_info:
                print(f"    ユーザー名: {account_info.get('username', 'N/A')}")
                print(f"    表示名: {account_info.get('full_name', 'N/A')}")
                print(f"    投稿数: {account_info.get('media_count', 'N/A')}")
                print(f"    フォロワー数: {account_info.get('follower_count', 'N/A')}")
        elif status == "login_required":
            print(f"\n[NG] {username}: ログインが必要")
            print(f"    {message}")
        elif status == "challenge_required":
            print(f"\n[WARN] {username}: チャレンジ認証が必要")
            print(f"    {message}")
        elif status == "ip_blacklisted":
            print(f"\n[NG] {username}: IPアドレスがブラックリスト")
            print(f"    {message}")
        elif status == "no_session":
            print(f"\n[NG] {username}: セッションファイルなし")
            print(f"    {message}")
        elif status == "duplicate_skipped":
            print(f"\n[SKIP] {username}: セッションID重複によりスキップ")
            print(f"    {message}")
        else:
            print(f"\n[ERROR] {username}: エラー")
            print(f"    {message}")

    print()
    print("=" * 60)


def main():
    """メイン関数"""
    print("=" * 60)
    print("Instagramアカウント ログイン状態確認ツール")
    print("=" * 60)
    print()

    # 設定ファイルのパス
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.json"

    if not Path(config_path).exists():
        print(f"[ERROR] 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)

    # すべてのアカウントを確認
    results = check_all_accounts(config_path)

    # サマリーを表示
    print_summary(results)

    # ログイン成功したアカウント数
    if results["logged_in"] == results["total_accounts"]:
        print("[SUCCESS] すべてのアカウントがログイン可能です！")
        sys.exit(0)
    elif results["logged_in"] > 0:
        print(f"[WARN] {results['logged_in']}/{results['total_accounts']}アカウントがログイン可能です")
        sys.exit(0)
    else:
        print("[ERROR] ログイン可能なアカウントがありません")
        sys.exit(1)


if __name__ == "__main__":
    main()

