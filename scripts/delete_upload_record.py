"""
データベースからアップロード履歴を削除するスクリプト
既存の投稿データで再テストする場合に使用
"""

import sqlite3
import sys
from pathlib import Path

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

DB_PATH = "data/upload_history.db"


def delete_post_record(post_id: str | None = None, instagram_id: str | None = None, location_id: str | None = None):
    """投稿のアップロード履歴を削除"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        conditions = []
        params = []

        if post_id:
            conditions.append("post_id = ?")
            params.append(post_id)
        
        if instagram_id:
            conditions.append("instagram_id = ?")
            params.append(instagram_id)
        
        if location_id:
            conditions.append("location_id = ?")
            params.append(location_id)

        if not conditions:
            print("[ERROR] 削除条件が指定されていません")
            conn.close()
            return False

        where_clause = "WHERE " + " AND ".join(conditions)

        # 削除前に件数を確認
        count_query = f"SELECT COUNT(*) FROM uploaded_posts {where_clause}"
        cursor.execute(count_query, params)
        count = cursor.fetchone()[0]

        if count == 0:
            print(f"[INFO] 削除対象の投稿が見つかりませんでした")
            conn.close()
            return False

        print(f"[INFO] {count}件の投稿を削除します")

        # 削除実行
        delete_query = f"DELETE FROM uploaded_posts {where_clause}"
        cursor.execute(delete_query, params)
        conn.commit()

        print(f"[OK] {count}件の投稿を削除しました")
        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] エラーが発生しました: {e}")
        return False


def list_posts(instagram_id: str | None = None, limit: int = 20):
    """投稿のアップロード履歴を一覧表示"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = []
        params = []

        if instagram_id:
            conditions.append("instagram_id = ?")
            params.append(instagram_id)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT * FROM uploaded_posts
            {where_clause}
            ORDER BY upload_date DESC
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("投稿が見つかりませんでした")
            conn.close()
            return

        print(f"\n{'='*80}")
        print(f"投稿アップロード履歴 ({len(rows)}件)")
        print(f"{'='*80}\n")

        for i, row in enumerate(rows, 1):
            print(f"[{i}] Post ID: {row['post_id']}")
            print(f"    Instagram ID: {row['instagram_id']}")
            print(f"    Location ID: {row['location_id']}")
            print(f"    投稿日時: {row['taken_at']}")
            print(f"    アップロード日時: {row['upload_date']}")
            print(f"    ステータス: {row['upload_status']}")
            print()

        conn.close()

    except Exception as e:
        print(f"[ERROR] エラーが発生しました: {e}")


def main():
    print("=" * 60)
    print("アップロード履歴削除ツール")
    print("=" * 60)
    print()

    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} list [instagram_id]")
        print(f"  python {sys.argv[0]} delete <post_id> [instagram_id] [location_id]")
        print()
        print("例:")
        print(f"  # 投稿一覧を表示")
        print(f"  python {sys.argv[0]} list hidanetest")
        print()
        print(f"  # 特定の投稿を削除")
        print(f"  python {sys.argv[0]} delete 3777007849613463626")
        print()
        print(f"  # 特定のInstagramアカウントのすべての投稿を削除")
        print(f"  python {sys.argv[0]} delete None hidanetest")
        print()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        instagram_id = sys.argv[2] if len(sys.argv) > 2 else None
        list_posts(instagram_id=instagram_id)
    elif command == "delete":
        if len(sys.argv) < 3:
            print("[ERROR] post_idが必要です")
            sys.exit(1)
        
        # --yesフラグで確認をスキップ
        skip_confirm = "--yes" in sys.argv or "-y" in sys.argv
        # フラグを除いた引数を取得
        args = [arg for arg in sys.argv[2:] if arg not in ["--yes", "-y"]]
        
        post_id = args[0] if len(args) > 0 and args[0].lower() != "none" else None
        instagram_id = args[1] if len(args) > 1 and args[1].lower() != "none" else None
        location_id = args[2] if len(args) > 2 and args[2].lower() != "none" else None

        if post_id is None and instagram_id is None:
            print("[ERROR] post_idまたはinstagram_idが必要です")
            sys.exit(1)

        # 確認
        print(f"削除条件:")
        if post_id:
            print(f"  Post ID: {post_id}")
        if instagram_id:
            print(f"  Instagram ID: {instagram_id}")
        if location_id:
            print(f"  Location ID: {location_id}")
        print()

        if not skip_confirm:
            try:
                response = input("削除しますか？ (y/N): ").strip().lower()
                if response != 'y' and response != 'yes':
                    print("[INFO] キャンセルしました")
                    sys.exit(0)
            except EOFError:
                print("[ERROR] 対話的入力ができません。--yesフラグを使用してください")
                sys.exit(1)

        success = delete_post_record(post_id=post_id, instagram_id=instagram_id, location_id=location_id)
        sys.exit(0 if success else 1)
    else:
        print(f"[ERROR] 不明なコマンド: {command}")
        print("有効なコマンド: list, delete")
        sys.exit(1)


if __name__ == "__main__":
    main()
