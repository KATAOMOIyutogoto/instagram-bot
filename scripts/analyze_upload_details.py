"""
アップロードログの詳細分析スクリプト
動画・画像が適切にアップロードされているか、重複がないかを詳細に確認します
"""

import json
import sys
from collections import defaultdict
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


def get_file_type(file_path: str) -> str:
    """ファイルパスからファイルタイプ（動画/画像）を判定"""
    file_path_lower = file_path.lower()
    video_extensions = [".mp4", ".mov", ".avi", ".wmv", ".webm", ".mkv"]
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    
    if any(file_path_lower.endswith(ext) for ext in video_extensions):
        return "video"
    elif any(file_path_lower.endswith(ext) for ext in image_extensions):
        return "image"
    else:
        return "unknown"


def analyze_uploads(logs: list[dict[str, Any]]):
    """アップロードログを詳細に分析"""
    uploaded_posts = []
    uploaded_stories = []
    skipped_posts = []
    skipped_stories = []
    
    # アップロードされた投稿とストーリーを分類
    for log in logs:
        upload_type = log.get("upload_type")
        upload_status = log.get("upload_status")
        skipped = log.get("skipped", False)
        
        if upload_type == "post":
            if upload_status == "uploaded" and not skipped:
                uploaded_posts.append(log)
            elif upload_status == "skipped" or skipped:
                skipped_posts.append(log)
        elif upload_type == "story":
            if upload_status == "uploaded" and not skipped:
                uploaded_stories.append(log)
            elif upload_status == "skipped" or skipped:
                skipped_stories.append(log)
    
    # 投稿の分析
    post_videos = []
    post_images = []
    post_by_instagram = defaultdict(list)
    post_by_location = defaultdict(list)
    
    for log in uploaded_posts:
        target_files = log.get("target_files", [])
        instagram_id = log.get("instagram_id")
        location_id = log.get("location_id")
        
        for file_path in target_files:
            file_type = get_file_type(file_path)
            if file_type == "video":
                post_videos.append(log)
            elif file_type == "image":
                post_images.append(log)
        
        if instagram_id:
            post_by_instagram[instagram_id].append(log)
        if location_id:
            post_by_location[location_id].append(log)
    
    # ストーリーの分析
    story_videos = []
    story_images = []
    story_by_instagram = defaultdict(list)
    story_by_location = defaultdict(list)
    
    for log in uploaded_stories:
        target_files = log.get("target_files", [])
        instagram_id = log.get("instagram_id")
        location_id = log.get("location_id")
        
        for file_path in target_files:
            file_type = get_file_type(file_path)
            if file_type == "video":
                story_videos.append(log)
            elif file_type == "image":
                story_images.append(log)
        
        if instagram_id:
            story_by_instagram[instagram_id].append(log)
        if location_id:
            story_by_location[location_id].append(log)
    
    # 重複チェック（Post ID / Story ID + Location ID）
    post_duplicates = defaultdict(list)
    story_duplicates = defaultdict(list)
    
    for log in uploaded_posts:
        post_id = log.get("post_id")
        location_id = log.get("location_id")
        if post_id and location_id:
            key = (post_id, location_id)
            post_duplicates[key].append(log)
    
    for log in uploaded_stories:
        story_id = log.get("story_id")
        location_id = log.get("location_id")
        if story_id and location_id:
            key = (story_id, location_id)
            story_duplicates[key].append(log)
    
    # 重複を見つける
    actual_post_duplicates = {k: v for k, v in post_duplicates.items() if len(v) > 1}
    actual_story_duplicates = {k: v for k, v in story_duplicates.items() if len(v) > 1}
    
    return {
        "uploaded_posts": {
            "total": len(uploaded_posts),
            "videos": len(set(log.get("post_id") for log in post_videos if log.get("post_id"))),
            "images": len(set(log.get("post_id") for log in post_images if log.get("post_id"))),
            "by_instagram": dict(post_by_instagram),
            "by_location": dict(post_by_location),
            "duplicates": actual_post_duplicates,
        },
        "uploaded_stories": {
            "total": len(uploaded_stories),
            "videos": len(set(log.get("story_id") for log in story_videos if log.get("story_id"))),
            "images": len(set(log.get("story_id") for log in story_images if log.get("story_id"))),
            "by_instagram": dict(story_by_instagram),
            "by_location": dict(story_by_location),
            "duplicates": actual_story_duplicates,
        },
        "skipped_posts": len(skipped_posts),
        "skipped_stories": len(skipped_stories),
    }


def print_detailed_report(logs: list[dict[str, Any]]):
    """詳細な分析レポートを表示"""
    print("=" * 80)
    print("アップロードログ詳細分析レポート")
    print("=" * 80)
    print()
    
    analysis = analyze_uploads(logs)
    
    print("【全体統計】")
    print(f"  総ログ数: {len(logs)}件")
    print()
    
    print("【投稿の詳細統計】")
    print(f"  アップロード済み: {analysis['uploaded_posts']['total']}件")
    print(f"  - 動画: {analysis['uploaded_posts']['videos']}件")
    print(f"  - 画像: {analysis['uploaded_posts']['images']}件")
    print(f"  スキップ済み: {analysis['skipped_posts']}件")
    print()
    
    print("【ストーリーの詳細統計】")
    print(f"  アップロード済み: {analysis['uploaded_stories']['total']}件")
    print(f"  - 動画: {analysis['uploaded_stories']['videos']}件")
    print(f"  - 画像: {analysis['uploaded_stories']['images']}件")
    print(f"  スキップ済み: {analysis['skipped_stories']}件")
    print()
    
    # 重複チェック
    print("=" * 80)
    print("【重複チェック】")
    print("=" * 80)
    print()
    
    post_dups = analysis['uploaded_posts']['duplicates']
    story_dups = analysis['uploaded_stories']['duplicates']
    
    print("【投稿の重複】")
    if post_dups:
        print(f"  [WARNING] {len(post_dups)}グループの重複が見つかりました:")
        for i, ((post_id, location_id), group) in enumerate(post_dups.items(), 1):
            print(f"    [{i}] Post ID: {post_id}, Location ID: {location_id}")
            print(f"        重複回数: {len(group)}回")
            for log in group:
                print(f"          - {log.get('upload_date', 'N/A')} ({log.get('instagram_id', 'N/A')})")
            print()
    else:
        print("  [OK] 重複は見つかりませんでした")
    print()
    
    print("【ストーリーの重複】")
    if story_dups:
        print(f"  [WARNING] {len(story_dups)}グループの重複が見つかりました:")
        for i, ((story_id, location_id), group) in enumerate(story_dups.items(), 1):
            print(f"    [{i}] Story ID: {story_id}, Location ID: {location_id}")
            print(f"        重複回数: {len(group)}回")
            for log in group:
                print(f"          - {log.get('upload_date', 'N/A')} ({log.get('instagram_id', 'N/A')})")
            print()
    else:
        print("  [OK] 重複は見つかりませんでした")
    print()
    
    # Instagram ID別の統計
    print("=" * 80)
    print("【Instagram ID別のアップロード統計（上位10件）】")
    print("=" * 80)
    print()
    
    post_by_insta = analysis['uploaded_posts']['by_instagram']
    story_by_insta = analysis['uploaded_stories']['by_instagram']
    
    all_instagram_ids = set(post_by_insta.keys()) | set(story_by_insta.keys())
    instagram_stats = []
    
    for insta_id in all_instagram_ids:
        post_count = len(post_by_insta.get(insta_id, []))
        story_count = len(story_by_insta.get(insta_id, []))
        total = post_count + story_count
        instagram_stats.append((insta_id, post_count, story_count, total))
    
    instagram_stats.sort(key=lambda x: x[3], reverse=True)
    
    print("  Instagram ID | 投稿 | ストーリー | 合計")
    print("  " + "-" * 60)
    for insta_id, post_count, story_count, total in instagram_stats[:10]:
        print(f"  {insta_id:30s} | {post_count:4d} | {story_count:8d} | {total:4d}")
    print()
    
    # 最近のアップロード（最新20件、動画と画像を区別）
    print("=" * 80)
    print("【最近のアップロード（最新20件）】")
    print("=" * 80)
    print()
    
    all_uploaded = []
    for log in logs:
        if log.get("upload_status") == "uploaded" and not log.get("skipped", False):
            all_uploaded.append(log)
    
    all_uploaded.sort(key=lambda x: x.get("upload_date", ""), reverse=True)
    
    for i, log in enumerate(all_uploaded[:20], 1):
        upload_type_jp = "投稿" if log.get("upload_type") == "post" else "ストーリー"
        target_files = log.get("target_files", [])
        file_types = []
        for file_path in target_files[:1]:  # 最初のファイルのみ
            file_type = get_file_type(file_path)
            file_types.append(file_type)
        
        file_type_str = ", ".join(set(file_types)) if file_types else "unknown"
        
        print(f"[{i}] {upload_type_jp} ({file_type_str})")
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
    
    # 重複がある場合はエラーコードを返す
    if post_dups or story_dups:
        print("\n[WARNING] 警告: 重複が見つかりました")
        sys.exit(1)
    else:
        print("\n[OK] すべて正常です。重複は見つかりませんでした。")
        sys.exit(0)


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
    
    print_detailed_report(logs)


if __name__ == "__main__":
    main()

