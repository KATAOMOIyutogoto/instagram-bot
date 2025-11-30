"""
アップロードログの重複チェックスクリプト
投稿とストーリーが適切にアップロードされ、重複がないかを確認します
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def load_upload_logs(log_file: str = "data/upload_mock_logs.json") -> list[dict[str, Any]]:
    """アップロードログを読み込む"""
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"[ERROR] ログファイルが見つかりません: {log_file}")
        return []

    try:
        with open(log_path, encoding="utf-8") as f:
            logs = json.load(f)
        return logs
    except Exception as e:
        print(f"[ERROR] ログファイルの読み込みに失敗しました: {e}")
        return []


def check_post_duplicates(logs: list[dict[str, Any]]) -> dict[str, Any]:
    """投稿の重複をチェック"""
    # アップロードされた投稿のみを抽出（スキップされたものは除外）
    uploaded_posts = [
        log
        for log in logs
        if log.get("upload_type") == "post"
        and log.get("upload_status") == "uploaded"
        and not log.get("skipped", False)
    ]

    # Post ID + Location ID でグループ化
    post_id_location_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    # Taken At + Instagram ID + Location ID でグループ化（Post IDがない場合）
    taken_at_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

    for log in uploaded_posts:
        post_id = log.get("post_id")
        location_id = log.get("location_id")
        instagram_id = log.get("instagram_id")
        taken_at = log.get("taken_at")

        if not location_id or not instagram_id or not taken_at:
            continue

        # Post IDベースの重複チェック
        if post_id:
            key = (post_id, location_id)
            post_id_location_groups[key].append(log)
        else:
            # Taken Atベースの重複チェック（Post IDがない場合）
            key = (taken_at, instagram_id, location_id)
            taken_at_groups[key].append(log)

    duplicates = []
    duplicate_count = 0

    # Post IDベースの重複をチェック
    for (post_id, location_id), group in post_id_location_groups.items():
        if len(group) > 1:
            duplicate_count += len(group) - 1  # 最初の1つ以外は重複
            duplicates.append({
                "type": "post_id",
                "post_id": post_id,
                "location_id": location_id,
                "count": len(group),
                "logs": group,
            })

    # Taken Atベースの重複をチェック
    for (taken_at, instagram_id, location_id), group in taken_at_groups.items():
        if len(group) > 1:
            duplicate_count += len(group) - 1  # 最初の1つ以外は重複
            duplicates.append({
                "type": "taken_at",
                "taken_at": taken_at,
                "instagram_id": instagram_id,
                "location_id": location_id,
                "count": len(group),
                "logs": group,
            })

    return {
        "total_uploaded": len(uploaded_posts),
        "duplicate_groups": len(duplicates),
        "duplicate_count": duplicate_count,
        "duplicates": duplicates,
    }


def check_story_duplicates(logs: list[dict[str, Any]]) -> dict[str, Any]:
    """ストーリーの重複をチェック"""
    # アップロードされたストーリーのみを抽出（スキップされたものは除外）
    uploaded_stories = [
        log
        for log in logs
        if log.get("upload_type") == "story"
        and log.get("upload_status") == "uploaded"
        and not log.get("skipped", False)
    ]

    # Story ID + Location ID でグループ化
    story_id_location_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    # Taken At + Instagram ID + Location ID でグループ化（Story IDがない場合）
    taken_at_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

    for log in uploaded_stories:
        story_id = log.get("story_id")
        location_id = log.get("location_id")
        instagram_id = log.get("instagram_id")
        taken_at = log.get("taken_at")

        if not location_id or not instagram_id or not taken_at:
            continue

        # Story IDベースの重複チェック
        if story_id:
            key = (story_id, location_id)
            story_id_location_groups[key].append(log)
        else:
            # Taken Atベースの重複チェック（Story IDがない場合）
            key = (taken_at, instagram_id, location_id)
            taken_at_groups[key].append(log)

    duplicates = []
    duplicate_count = 0

    # Story IDベースの重複をチェック
    for (story_id, location_id), group in story_id_location_groups.items():
        if len(group) > 1:
            duplicate_count += len(group) - 1  # 最初の1つ以外は重複
            duplicates.append({
                "type": "story_id",
                "story_id": story_id,
                "location_id": location_id,
                "count": len(group),
                "logs": group,
            })

    # Taken Atベースの重複をチェック
    for (taken_at, instagram_id, location_id), group in taken_at_groups.items():
        if len(group) > 1:
            duplicate_count += len(group) - 1  # 最初の1つ以外は重複
            duplicates.append({
                "type": "taken_at",
                "taken_at": taken_at,
                "instagram_id": instagram_id,
                "location_id": location_id,
                "count": len(group),
                "logs": group,
            })

    return {
        "total_uploaded": len(uploaded_stories),
        "duplicate_groups": len(duplicates),
        "duplicate_count": duplicate_count,
        "duplicates": duplicates,
    }


def print_report(logs: list[dict[str, Any]]):
    """アップロードログの分析レポートを表示"""
    print("=" * 80)
    print("アップロードログ分析レポート")
    print("=" * 80)
    print()

    # 全体統計
    total_logs = len(logs)
    posts = [log for log in logs if log.get("upload_type") == "post"]
    stories = [log for log in logs if log.get("upload_type") == "story"]
    
    uploaded_posts = [
        log
        for log in posts
        if log.get("upload_status") == "uploaded" and not log.get("skipped", False)
    ]
    skipped_posts = [
        log
        for log in posts
        if log.get("upload_status") == "skipped" or log.get("skipped", False)
    ]
    failed_posts = [
        log
        for log in posts
        if log.get("upload_status") == "failed"
    ]

    uploaded_stories = [
        log
        for log in stories
        if log.get("upload_status") == "uploaded" and not log.get("skipped", False)
    ]
    skipped_stories = [
        log
        for log in stories
        if log.get("upload_status") == "skipped" or log.get("skipped", False)
    ]
    failed_stories = [
        log
        for log in stories
        if log.get("upload_status") == "failed"
    ]

    print("【全体統計】")
    print(f"  総ログ数: {total_logs}件")
    print(f"  - 投稿: {len(posts)}件")
    print(f"  - ストーリー: {len(stories)}件")
    print()

    print("【投稿の統計】")
    print(f"  アップロード済み: {len(uploaded_posts)}件")
    print(f"  スキップ済み: {len(skipped_posts)}件")
    print(f"  失敗: {len(failed_posts)}件")
    print()

    print("【ストーリーの統計】")
    print(f"  アップロード済み: {len(uploaded_stories)}件")
    print(f"  スキップ済み: {len(skipped_stories)}件")
    print(f"  失敗: {len(failed_stories)}件")
    print()

    # 重複チェック
    print("=" * 80)
    print("【重複チェック】")
    print("=" * 80)
    print()

    post_result = check_post_duplicates(logs)
    story_result = check_story_duplicates(logs)

    print("【投稿の重複チェック】")
    print(f"  アップロード済み投稿数: {post_result['total_uploaded']}件")
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
            for log in dup['logs']:
                print(f"          - {log.get('upload_date', 'N/A')}")
            print()
    else:
        print("  [OK] 重複は見つかりませんでした")
    print()

    print("【ストーリーの重複チェック】")
    print(f"  アップロード済みストーリー数: {story_result['total_uploaded']}件")
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
            for log in dup['logs']:
                print(f"          - {log.get('upload_date', 'N/A')}")
            print()
    else:
        print("  [OK] 重複は見つかりませんでした")
    print()

    # 最近のアップロード（最新10件）
    print("=" * 80)
    print("【最近のアップロード（最新10件）】")
    print("=" * 80)
    print()

    all_uploaded = uploaded_posts + uploaded_stories
    all_uploaded.sort(key=lambda x: x.get("upload_date", ""), reverse=True)

    for i, log in enumerate(all_uploaded[:10], 1):
        upload_type_jp = "投稿" if log.get("upload_type") == "post" else "ストーリー"
        print(f"[{i}] {upload_type_jp}")
        print(f"    Instagram ID: {log.get('instagram_id')}")
        print(f"    Location ID: {log.get('location_id')}")
        print(f"    投稿日時: {log.get('taken_at')}")
        print(f"    アップロード日時: {log.get('upload_date')}")
        if log.get("post_id"):
            print(f"    Post ID: {log.get('post_id')}")
        if log.get("story_id"):
            print(f"    Story ID: {log.get('story_id')}")
        print()

    print("=" * 80)
    print("分析完了")
    print("=" * 80)


def main():
    """メイン関数"""
    log_file = "data/upload_mock_logs.json"
    
    if len(sys.argv) > 1:
        log_file = sys.argv[1]

    print(f"[INFO] ログファイルを読み込んでいます: {log_file}")
    logs = load_upload_logs(log_file)

    if not logs:
        print("[ERROR] ログが読み込めませんでした")
        sys.exit(1)

    print(f"[OK] {len(logs)}件のログを読み込みました")
    print()

    print_report(logs)

    # 重複が見つかった場合はエラーコードを返す
    post_result = check_post_duplicates(logs)
    story_result = check_story_duplicates(logs)

    if post_result['duplicate_groups'] > 0 or story_result['duplicate_groups'] > 0:
        print("\n[WARNING] 警告: 重複が見つかりました")
        sys.exit(1)
    else:
        print("\n[OK] 重複は見つかりませんでした")
        sys.exit(0)


if __name__ == "__main__":
    main()

