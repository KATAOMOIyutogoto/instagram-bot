"""
ブラウザから取得したセッション情報でセッションファイルを更新するスクリプト
"""

import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def update_session_from_browser(
    session_file: str,
    sessionid: str,
    ds_user_id: str | None = None,
):
    """
    ブラウザから取得したセッション情報でセッションファイルを更新

    Args:
        session_file: セッションファイルのパス
        sessionid: ブラウザから取得したsessionidクッキー
        ds_user_id: ユーザーID（sessionidから自動抽出される場合もある）
    """
    session_path = Path(session_file)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    # 既存のセッションファイルを読み込む（あれば）
    if session_path.exists():
        try:
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            print(f"[INFO] 既存のセッションファイルを読み込みました: {session_file}")
        except Exception as e:
            print(f"[WARNING] セッションファイルの読み込みに失敗しました: {e}")
            print("[INFO] 新規セッションファイルを作成します")
            session_data = {}
    else:
        print(f"[INFO] 新規セッションファイルを作成します: {session_file}")
        session_data = {}

    # authorization_dataセクションを初期化（存在しない場合）
    if "authorization_data" not in session_data:
        session_data["authorization_data"] = {}

    # sessionidを更新
    session_data["authorization_data"]["sessionid"] = sessionid

    # ds_user_idを設定（指定された場合、または既存の値がある場合）
    if ds_user_id:
        session_data["authorization_data"]["ds_user_id"] = ds_user_id
    elif "ds_user_id" not in session_data.get("authorization_data", {}):
        # sessionidからユーザーIDを抽出（形式: "ユーザーID%3A..."）
        try:
            if "%3A" in sessionid:
                extracted_user_id = sessionid.split("%3A")[0]
                session_data["authorization_data"]["ds_user_id"] = extracted_user_id
                print(f"[INFO] sessionidからユーザーIDを抽出しました: {extracted_user_id}")
            elif ":" in sessionid:
                extracted_user_id = sessionid.split(":")[0]
                session_data["authorization_data"]["ds_user_id"] = extracted_user_id
                print(f"[INFO] sessionidからユーザーIDを抽出しました: {extracted_user_id}")
        except Exception as e:
            print(f"[WARNING] ユーザーIDの自動抽出に失敗しました: {e}")

    # その他の必須フィールドが存在しない場合はデフォルト値を設定
    if "uuids" not in session_data:
        session_data["uuids"] = {}
    if "cookies" not in session_data:
        session_data["cookies"] = {}

    # バックアップを作成
    backup_path = session_path.with_suffix(".json.backup")
    if session_path.exists():
        try:
            import shutil

            shutil.copy2(session_path, backup_path)
            print(f"[INFO] バックアップを作成しました: {backup_path}")
        except Exception as e:
            print(f"[WARNING] バックアップの作成に失敗しました: {e}")

    # セッションファイルを保存
    try:
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=4, ensure_ascii=False)
        print(f"[OK] セッションファイルを更新しました: {session_file}")
        print(f"\n更新されたセッション情報:")
        print(f"  sessionid: {sessionid[:50]}...")
        print(f"  ds_user_id: {session_data['authorization_data'].get('ds_user_id', 'N/A')}")
        return True
    except Exception as e:
        print(f"[ERROR] セッションファイルの保存に失敗しました: {e}")
        return False


def main():
    """メイン関数"""
    print("=" * 60)
    print("ブラウザセッション情報でセッションファイルを更新")
    print("=" * 60)
    print()

    if len(sys.argv) < 3:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <セッションファイル> <sessionid> [ds_user_id]")
        print()
        print("例:")
        print(f'  python {sys.argv[0]} data/session_account1.json "78760622757%3A..."')
        print(f'  python {sys.argv[0]} data/session_account1.json "78760622757%3A..." "78760622757"')
        print()
        print("ブラウザからsessionidを取得する方法:")
        print()
        print("【方法1: Networkタブから取得（推奨）】")
        print("  1. Instagramにログイン")
        print("  2. 開発者ツールを開く（F12）")
        print("  3. Networkタブを開く")
        print("  4. ページをリロード（F5）")
        print("  5. 任意のリクエストをクリック")
        print("  6. Headersタブ → Request Headers → Cookie")
        print("  7. Cookie文字列の中から 'sessionid=...' の部分を探してコピー")
        print()
        print("【方法2: Applicationタブから取得】")
        print("  1. Instagramにログイン")
        print("  2. 開発者ツールを開く（F12）")
        print("  3. Applicationタブ → Cookies → https://www.instagram.com")
        print("  4. 'sessionid'という名前のクッキーの値をコピー")
        sys.exit(1)

    session_file = sys.argv[1]
    sessionid = sys.argv[2]
    ds_user_id = sys.argv[3] if len(sys.argv) > 3 else None

    success = update_session_from_browser(session_file, sessionid, ds_user_id)

    if success:
        print()
        print("=" * 60)
        print("次のステップ:")
        print("  1. Botを実行してセッション情報が有効か確認")
        print("  2. 有効な場合は、そのまま使用できます")
        print("=" * 60)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

