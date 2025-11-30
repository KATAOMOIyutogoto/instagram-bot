"""
データベース内の重複チェックスクリプト
データベースに記録されている投稿・ストーリーの重複を確認します
"""

import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


DB_PATH = "data/upload_history.db"


def check_post_duplicates():
    """投稿の重複をチェック"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # すべてのアップロード済み投稿を取得
        cursor.execute("""
            SELECT post_id, instagram_id, location_id, taken_at, upload_date, file_path
            FROM uploaded_posts
            WHERE upload_status = 'success'
            ORDER BY upload_date DESC
        """)

        rows = cursor.fetchall()

        # Post ID + Location ID でグループ化
        post_id_groups: dict[tuple[str, str], list] = defaultdict(list)
        # Taken At + Instagram ID + Location ID でグループ化
        taken_at_groups: dict[tuple[str, str, str], list] = defaultdict(list)

        for row in rows:
            post_id = row['post_id']
            location_id = row['location_id']
            instagram_id = row['instagram_id']
            taken_at = row['taken_at']

            if post_id:
                key = (post_id, location_id)
                post_id_groups[key].append(dict(row))
            else:
                key = (taken_at, instagram_id, location_id)
                taken_at_groups[key].append(dict(row))

        duplicates = []
        
        # Post IDベースの重複をチェック
        for (post_id, location_id), group in post_id_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "type": "post_id",
                    "post_id": post_id,
                    "location_id": location_id,
                    "count": len(group),
                    "records": group,
                })

        # Taken Atベースの重複をチェック
        for (taken_at, instagram_id, location_id), group in taken_at_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "type": "taken_at",
                    "taken_at": taken_at,
                    "instagram_id": instagram_id,
                    "location_id": location_id,
                    "count": len(group),
                    "records": group,
                })

        conn.close()

        return {
            "total": len(rows),
            "duplicate_groups": len(duplicates),
            "duplicate_count": sum(d['count'] - 1 for d in duplicates),
            "duplicates": duplicates,
        }

    except Exception as e:
        print(f"[ERROR] データベースの読み込みエラー: {e}")
        return None


def check_story_duplicates():
    """ストーリーの重複をチェック"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # すべてのアップロード済みストーリーを取得
        cursor.execute("""
            SELECT story_id, instagram_id, location_id, taken_at, upload_date, file_path
            FROM uploaded_stories
            WHERE upload_status = 'success'
            ORDER BY upload_date DESC
        """)

        rows = cursor.fetchall()

        # Story ID + Location ID でグループ化
        story_id_groups: dict[tuple[str, str], list] = defaultdict(list)
        # Taken At + Instagram ID + Location ID でグループ化
        taken_at_groups: dict[tuple[str, str, str], list] = defaultdict(list)

        for row in rows:
            story_id = row['story_id']
            location_id = row['location_id']
            instagram_id = row['instagram_id']
            taken_at = row['taken_at']

            if story_id:
                key = (story_id, location_id)
                story_id_groups[key].append(dict(row))
            else:
                key = (taken_at, instagram_id, location_id)
                taken_at_groups[key].append(dict(row))

        duplicates = []
        
        # Story IDベースの重複をチェック
        for (story_id, location_id), group in story_id_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "type": "story_id",
                    "story_id": story_id,
                    "location_id": location_id,
                    "count": len(group),
                    "records": group,
                })

        # Taken Atベースの重複をチェック
        for (taken_at, instagram_id, location_id), group in taken_at_groups.items():
            if len(group) > 1:
                duplicates.append({
                    "type": "taken_at",
                    "taken_at": taken_at,
                    "instagram_id": instagram_id,
                    "location_id": location_id,
                    "count": len(group),
                    "records": group,
                })

        conn.close()

        return {
            "total": len(rows),
            "duplicate_groups": len(duplicates),
            "duplicate_count": sum(d['count'] - 1 for d in duplicates),
            "duplicates": duplicates,
        }

    except Exception as e:
        print(f"[ERROR] データベースの読み込みエラー: {e}")
        return None


def print_report():
    """レポートを表示"""
    print("=" * 80)
    print("データベース重複チェックレポート")
    print("=" * 80)
    print()

    post_result = check_post_duplicates()
    story_result = check_story_duplicates()

    if post_result is None or story_result is None:
        print("[ERROR] データベースの読み込みに失敗しました")
        sys.exit(1)

    print("【投稿の重複チェック】")
    print(f"  データベース内のアップロード済み投稿数: {post_result['total']}件")
    print(f"  重複グループ数: {post_result['duplicate_groups']}グループ")
    print(f"  重複投稿数: {post_result['duplicate_count']}件")
    print()

    if post_result['duplicates']:
        print("  [WARNING] 重複が見つかりました:")
        for i, dup in enumerate(post_result['duplicates'], 1):
            if dup['type'] == 'post_id':
                print(f"    [{i}] Post ID: {dup['post_id']}, Location ID: {dup['location_id']}")
            else:
                print(f"    [{i}] Taken At: {dup['taken_at']}, Instagram ID: {dup['instagram_id']}, Location ID: {dup['location_id']}")
            print(f"        重複回数: {dup['count']}回")
            print(f"        アップロード日時:")
            for record in dup['records']:
                print(f"          - {record.get('upload_date', 'N/A')}")
            print()
    else:
        print("  [OK] 重複は見つかりませんでした")
    print()

    print("【ストーリーの重複チェック】")
    print(f"  データベース内のアップロード済みストーリー数: {story_result['total']}件")
    print(f"  重複グループ数: {story_result['duplicate_groups']}グループ")
    print(f"  重複ストーリー数: {story_result['duplicate_count']}件")
    print()

    if story_result['duplicates']:
        print("  [WARNING] 重複が見つかりました:")
        for i, dup in enumerate(story_result['duplicates'], 1):
            if dup['type'] == 'story_id':
                print(f"    [{i}] Story ID: {dup['story_id']}, Location ID: {dup['location_id']}")
            else:
                print(f"    [{i}] Taken At: {dup['taken_at']}, Instagram ID: {dup['instagram_id']}, Location ID: {dup['location_id']}")
            print(f"        重複回数: {dup['count']}回")
            print(f"        アップロード日時:")
            for record in dup['records']:
                print(f"          - {record.get('upload_date', 'N/A')}")
            print()
    else:
        print("  [OK] 重複は見つかりませんでした")
    print()

    print("=" * 80)
    print("分析完了")
    print("=" * 80)

    # 重複が見つかった場合はエラーコードを返す
    if post_result['duplicate_groups'] > 0 or story_result['duplicate_groups'] > 0:
        print("\n[WARNING] 警告: 重複が見つかりました")
        sys.exit(1)
    else:
        print("\n[OK] 重複は見つかりませんでした")
        sys.exit(0)


def main():
    """メイン関数"""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"[ERROR] データベースファイルが見つかりません: {DB_PATH}")
        sys.exit(1)

    print_report()


if __name__ == "__main__":
    main()

