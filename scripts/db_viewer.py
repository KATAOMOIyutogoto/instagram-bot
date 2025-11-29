"""
データベースビューアー
upload_history.dbの内容を表示・検索するツール
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = "data/upload_history.db"


def print_table(table_name: str, limit: int = 20):
    """テーブルの内容を表示"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # テーブルの存在確認
        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """,
            (table_name,),
        )

        if not cursor.fetchone():
            print(f"テーブル '{table_name}' が見つかりません。")
            conn.close()
            return

        # データを取得
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()

        if not rows:
            print(f"テーブル '{table_name}' にデータがありません。")
            conn.close()
            return

        # カラム名を取得
        columns = [description[0] for description in cursor.description]

        print(f"\n{'='*80}")
        print(f"テーブル: {table_name}")
        print(f"件数: {len(rows)}件")
        print(f"{'='*80}\n")

        # ヘッダーを表示
        print(" | ".join(columns))
        print("-" * 80)

        # データを表示
        for row in rows:
            values = []
            for col in columns:
                value = row[col]
                if value is None:
                    values.append("NULL")
                elif isinstance(value, str) and len(value) > 30:
                    values.append(value[:27] + "...")
                else:
                    values.append(str(value))
            print(" | ".join(values))

        conn.close()

    except Exception as e:
        print(f"エラー: {e}")


def list_tables():
    """すべてのテーブルを一覧表示"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """
        )

        tables = cursor.fetchall()

        print("\nデータベース内のテーブル:")
        print("-" * 40)
        for table in tables:
            # 各テーブルのレコード数を取得
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]} ({count}件)")

        conn.close()

    except Exception as e:
        print(f"エラー: {e}")


def search_posts(instagram_id: str | None = None, store_id: str | None = None):
    """投稿のアップロード履歴を検索"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = []
        params = []

        if instagram_id:
            conditions.append("instagram_id = ?")
            params.append(instagram_id)

        if store_id:
            conditions.append("store_id = ?")
            params.append(store_id)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT * FROM uploaded_posts
            {where_clause}
            ORDER BY upload_date DESC
            LIMIT 50
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("該当する投稿が見つかりませんでした。")
            conn.close()
            return

        print(f"\n{'='*80}")
        print(f"投稿アップロード履歴 ({len(rows)}件)")
        print(f"{'='*80}\n")

        for i, row in enumerate(rows, 1):
            print(f"[{i}] 投稿ID: {row['post_id']}")
            print(f"    Instagram ID: {row['instagram_id']}")
            print(f"    アカウントID: {row.get('account_id', 'N/A')}")
            print(f"    ロケーションID: {row.get('location_id', 'N/A')}")
            print(f"    投稿日時: {row['taken_at']}")
            print(f"    アップロード日時: {row['upload_date']}")
            print(f"    ステータス: {row['upload_status']}")
            print(f"    ファイルパス: {row['file_path']}")
            print()

        conn.close()

    except Exception as e:
        print(f"エラー: {e}")


def search_stories(
    instagram_id: str | None = None, account_id: str | None = None, location_id: str | None = None
):
    """ストーリーのアップロード履歴を検索"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = []
        params = []

        if instagram_id:
            conditions.append("instagram_id = ?")
            params.append(instagram_id)

        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)

        if location_id:
            conditions.append("location_id = ?")
            params.append(location_id)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT * FROM uploaded_stories
            {where_clause}
            ORDER BY upload_date DESC
            LIMIT 50
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("該当するストーリーが見つかりませんでした。")
            conn.close()
            return

        print(f"\n{'='*80}")
        print(f"ストーリーアップロード履歴 ({len(rows)}件)")
        print(f"{'='*80}\n")

        for i, row in enumerate(rows, 1):
            print(f"[{i}] ストーリーID: {row['story_id']}")
            print(f"    Instagram ID: {row['instagram_id']}")
            print(f"    アカウントID: {row.get('account_id', 'N/A')}")
            print(f"    ロケーションID: {row.get('location_id', 'N/A')}")
            print(f"    投稿日時: {row['taken_at']}")
            print(f"    アップロード日時: {row['upload_date']}")
            print(f"    ステータス: {row['upload_status']}")
            print(f"    ファイルパス: {row['file_path']}")
            print()

        conn.close()

    except Exception as e:
        print(f"エラー: {e}")


def show_execution_logs(limit: int = 20):
    """実行ログを表示"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM execution_logs
            ORDER BY started_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()

        if not rows:
            print("実行ログがありません。")
            conn.close()
            return

        print(f"\n{'='*80}")
        print(f"実行ログ ({len(rows)}件)")
        print(f"{'='*80}\n")

        for i, row in enumerate(rows, 1):
            print(f"[{i}] {row['started_at']}")
            print(f"    タイプ: {row['execution_type']}")
            print(f"    ステータス: {row['status']}")
            print(f"    メッセージ: {row['message']}")
            if row["instagram_id"]:
                print(f"    Instagram ID: {row['instagram_id']}")
            if row.get("account_id"):
                print(f"    アカウントID: {row['account_id']}")
            if row.get("location_id"):
                print(f"    ロケーションID: {row['location_id']}")
            print(f"    投稿数: {row['posts_count']}, ストーリー数: {row['stories_count']}")
            print(
                f"    成功: {row['success_count']}, 失敗: {row['failed_count']}, スキップ: {row['skipped_count']}"
            )
            if row["execution_time_seconds"]:
                print(f"    実行時間: {row['execution_time_seconds']:.2f}秒")
            print()

        conn.close()

    except Exception as e:
        print(f"エラー: {e}")


def show_location_mappings():
    """ロケーションマッピングを表示"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM instagram_location_mapping
            ORDER BY instagram_id, account_id, location_id
        """
        )

        rows = cursor.fetchall()

        if not rows:
            print("ロケーションマッピングがありません。")
            conn.close()
            return

        print(f"\n{'='*80}")
        print(f"ロケーションマッピング ({len(rows)}件)")
        print(f"{'='*80}\n")

        for row in rows:
            print(f"Instagram ID: {row['instagram_id']}")
            print(f"  アカウントID: {row['account_id']}")
            print(f"  ロケーションID: {row['location_id']}")
            print(f"  作成日時: {row['created_at']}")
            print()

        conn.close()

    except Exception as e:
        print(f"エラー: {e}")


def main():
    """メイン関数"""
    if not Path(DB_PATH).exists():
        print(f"データベースファイル '{DB_PATH}' が見つかりません。")
        return

    if len(sys.argv) < 2:
        print("\nデータベースビューアー")
        print("=" * 80)
        print("\n使用方法:")
        print("  python db_viewer.py list                    # テーブル一覧")
        print("  python db_viewer.py tables                 # すべてのテーブルを表示")
        print("  python db_viewer.py posts                  # 投稿履歴を表示")
        print("  python db_viewer.py posts <instagram_id>    # 特定のInstagram IDの投稿履歴")
        print("  python db_viewer.py stories                # ストーリー履歴を表示")
        print("  python db_viewer.py stories <instagram_id> # 特定のInstagram IDのストーリー履歴")
        print("  python db_viewer.py logs                   # 実行ログを表示")
        print("  python db_viewer.py stores                 # ロケーションマッピングを表示")
        print("  python db_viewer.py table <table_name>     # 特定のテーブルを表示")
        print()
        return

    command = sys.argv[1].lower()

    if command == "list" or command == "tables":
        list_tables()

    elif command == "posts":
        instagram_id = sys.argv[2] if len(sys.argv) > 2 else None
        account_id = sys.argv[3] if len(sys.argv) > 3 else None
        location_id = sys.argv[4] if len(sys.argv) > 4 else None
        search_posts(instagram_id=instagram_id, account_id=account_id, location_id=location_id)

    elif command == "stories":
        instagram_id = sys.argv[2] if len(sys.argv) > 2 else None
        account_id = sys.argv[3] if len(sys.argv) > 3 else None
        location_id = sys.argv[4] if len(sys.argv) > 4 else None
        search_stories(instagram_id=instagram_id, account_id=account_id, location_id=location_id)

    elif command == "logs":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 20
        show_execution_logs(limit=limit)

    elif command == "stores" or command == "locations":
        show_location_mappings()

    elif command == "table":
        if len(sys.argv) < 3:
            print("テーブル名を指定してください。")
            return
        table_name = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 20
        print_table(table_name, limit=limit)

    else:
        print(f"不明なコマンド: {command}")


if __name__ == "__main__":
    main()
