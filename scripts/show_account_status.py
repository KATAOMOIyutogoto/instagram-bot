"""
アカウント状態を表示するスクリプト
"""
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main():
    """メイン関数"""
    config_path = Path("config/config.json")
    if not config_path.exists():
        print(f"[ERROR] 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    accounts = config.get("instagram_accounts", [])

    print("=" * 60)
    print("アカウント状態一覧")
    print("=" * 60)
    print()

    logged_in_count = 0
    no_session_count = 0

    logged_in_accounts = []
    no_session_accounts = []

    for i, acc in enumerate(accounts, 1):
        username = acc.get("username", "unknown")
        session_file = acc.get("session_file", "")
        exists = Path(session_file).exists() if session_file else False

        if exists:
            status = "[OK] セッションファイルあり"
            logged_in_count += 1
            logged_in_accounts.append((i, username, session_file))
        else:
            status = "[NG] セッションファイルなし"
            no_session_count += 1
            no_session_accounts.append((i, username, session_file))

        print(f"{i}. {username}")
        print(f"   セッションファイル: {session_file}")
        print(f"   状態: {status}")
        print()

    print("=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"総アカウント数: {len(accounts)}")
    print(f"ログイン可能: {logged_in_count}アカウント")
    print(f"セッションファイル未作成: {no_session_count}アカウント")
    print()

    if logged_in_accounts:
        print("=" * 60)
        print("[OK] ログイン可能なアカウント")
        print("=" * 60)
        for i, username, session_file in logged_in_accounts:
            print(f"  {i}. {username}")
            print(f"     セッションファイル: {session_file}")
        print()

    if no_session_accounts:
        print("=" * 60)
        print("[NG] セッションファイルを作成する必要があるアカウント")
        print("=" * 60)
        for i, username, session_file in no_session_accounts:
            print(f"  {i}. {username}")
            print(f"     作成するセッションファイル: {session_file}")
            print(f"     コマンド例:")
            print(f'     python scripts/update_session_from_browser.py {session_file} "SESSION_ID"')
            print()


if __name__ == "__main__":
    main()

