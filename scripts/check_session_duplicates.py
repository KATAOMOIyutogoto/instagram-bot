"""
セッションIDの重複をチェックするスクリプト
"""
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def extract_user_id_from_sessionid(sessionid: str) -> str | None:
    """sessionidからユーザーIDを抽出"""
    try:
        if "%3A" in sessionid:
            return sessionid.split("%3A")[0]
        elif ":" in sessionid:
            return sessionid.split(":")[0]
        return None
    except:
        return None


def check_session_duplicates():
    """セッションIDの重複をチェック"""
    config_path = Path("config/config.json")
    if not config_path.exists():
        print(f"[ERROR] 設定ファイルが見つかりません: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    accounts = config.get("instagram_accounts", [])

    print("=" * 60)
    print("セッションID重複チェック")
    print("=" * 60)
    print()

    user_id_map = {}  # user_id -> [(username, session_file), ...]
    duplicates_found = False

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
                user_id_map[user_id].append((username, session_file, sessionid[:50] + "..."))

        except Exception as e:
            print(f"[WARNING] {username} ({session_file}): 読み込みエラー - {e}")
            continue

    # 重複を確認
    for user_id, accounts_list in user_id_map.items():
        if len(accounts_list) > 1:
            duplicates_found = True
            print(f"[WARN] ユーザーID {user_id} が複数のアカウントで使用されています:")
            for username, session_file, sessionid_preview in accounts_list:
                print(f"  - {username} ({session_file})")
                print(f"    sessionid: {sessionid_preview}")
            print()

    if not duplicates_found:
        print("[OK] セッションIDの重複は見つかりませんでした")
        print()
        print("現在のセッションID一覧:")
        for user_id, accounts_list in sorted(user_id_map.items()):
            for username, session_file, sessionid_preview in accounts_list:
                print(f"  {username}: ユーザーID {user_id}")
        print()
    else:
        print("[ERROR] 重複が見つかりました。各アカウントは異なるセッションIDを使用する必要があります。")
        sys.exit(1)


if __name__ == "__main__":
    check_session_duplicates()

