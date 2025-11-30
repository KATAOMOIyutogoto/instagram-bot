"""
アルバム投稿（複数写真）のアップロード確認スクリプト
1つの投稿に複数の写真がある場合、全ての写真がアップロードされているかを確認します
"""

import json
import sys
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


def analyze_album_uploads(logs: list[dict[str, Any]]):
    """アルバム投稿（複数ファイル）のアップロードを分析"""
    album_posts = []  # 複数ファイルを持つ投稿
    single_posts = []  # 単一ファイルの投稿
    
    for log in logs:
        if log.get("upload_type") != "post":
            continue
        
        target_files = log.get("target_files", [])
        file_count = len(target_files)
        
        if file_count > 1:
            album_posts.append(log)
        elif file_count == 1:
            single_posts.append(log)
    
    # アルバム投稿の分析
    album_analysis = {
        "total": len(album_posts),
        "uploaded": 0,
        "skipped": 0,
        "failed": 0,
        "incomplete_uploads": [],  # アップロード済みだが、ファイル数が一致しないもの
        "complete_uploads": [],  # すべてのファイルがアップロードされたもの
    }
    
    for log in album_posts:
        target_files = log.get("target_files", [])
        uploaded_urls = log.get("uploaded_urls", [])
        upload_status = log.get("upload_status", "")
        skipped = log.get("skipped", False)
        
        target_count = len(target_files)
        uploaded_count = len(uploaded_urls)
        
        if upload_status == "uploaded" and not skipped:
            album_analysis["uploaded"] += 1
            if uploaded_count == target_count:
                album_analysis["complete_uploads"].append({
                    "log": log,
                    "target_count": target_count,
                    "uploaded_count": uploaded_count,
                })
            else:
                album_analysis["incomplete_uploads"].append({
                    "log": log,
                    "target_count": target_count,
                    "uploaded_count": uploaded_count,
                })
        elif upload_status == "skipped" or skipped:
            album_analysis["skipped"] += 1
        else:
            album_analysis["failed"] += 1
    
    return {
        "album_posts": album_analysis,
        "single_posts": {
            "total": len(single_posts),
        },
    }


def print_report(logs: list[dict[str, Any]]):
    """アルバム投稿の分析レポートを表示"""
    print("=" * 80)
    print("アルバム投稿（複数写真）アップロード確認レポート")
    print("=" * 80)
    print()
    
    analysis = analyze_album_uploads(logs)
    
    album_info = analysis["album_posts"]
    
    print("【アルバム投稿（複数写真）の統計】")
    print(f"  総アルバム投稿数: {album_info['total']}件")
    print(f"  アップロード済み: {album_info['uploaded']}件")
    print(f"  スキップ済み: {album_info['skipped']}件")
    print(f"  失敗: {album_info['failed']}件")
    print()
    
    print("【アルバム投稿の詳細分析】")
    print(f"  すべてのファイルがアップロードされた投稿: {len(album_info['complete_uploads'])}件")
    print(f"  ファイル数が一致しない投稿: {len(album_info['incomplete_uploads'])}件")
    print()
    
    # 完全にアップロードされたアルバム投稿
    if album_info['complete_uploads']:
        print("=" * 80)
        print("【完全にアップロードされたアルバム投稿（最新10件）】")
        print("=" * 80)
        print()
        
        for i, item in enumerate(album_info['complete_uploads'][:10], 1):
            log = item["log"]
            print(f"[{i}] Post ID: {log.get('post_id')}")
            print(f"    Instagram ID: {log.get('instagram_id')}")
            print(f"    Location ID: {log.get('location_id')}")
            print(f"    投稿日時: {log.get('taken_at')}")
            print(f"    アップロード日時: {log.get('upload_date')}")
            print(f"    ファイル数: {item['target_count']}件（すべてアップロード済み）")
            print(f"    ファイル一覧:")
            for j, file_path in enumerate(log.get('target_files', [])[:5], 1):  # 最初の5件のみ表示
                file_name = Path(file_path).name
                print(f"      {j}. {file_name}")
            if item['target_count'] > 5:
                print(f"      ... 他 {item['target_count'] - 5}件")
            print()
    
    # ファイル数が一致しない投稿
    if album_info['incomplete_uploads']:
        print("=" * 80)
        print("[WARNING] ファイル数が一致しない投稿が見つかりました")
        print("=" * 80)
        print()
        
        for i, item in enumerate(album_info['incomplete_uploads'], 1):
            log = item["log"]
            print(f"[{i}] Post ID: {log.get('post_id')}")
            print(f"    Instagram ID: {log.get('instagram_id')}")
            print(f"    Location ID: {log.get('location_id')}")
            print(f"    投稿日時: {log.get('taken_at')}")
            print(f"    アップロード日時: {log.get('upload_date')}")
            print(f"    対象ファイル数: {item['target_count']}件")
            print(f"    アップロード済みURL数: {item['uploaded_count']}件")
            print(f"    ⚠️ 差分: {item['target_count'] - item['uploaded_count']}件がアップロードされていない可能性があります")
            print(f"    対象ファイル一覧:")
            for j, file_path in enumerate(log.get('target_files', []), 1):
                file_name = Path(file_path).name
                print(f"      {j}. {file_name}")
            print(f"    アップロード済みURL一覧:")
            for j, url in enumerate(log.get('uploaded_urls', []), 1):
                url_path = url.replace("file:///", "").replace("\\", "/")
                file_name = Path(url_path).name
                print(f"      {j}. {file_name}")
            print()
    else:
        print("=" * 80)
        print("[OK] すべてのアルバム投稿で、すべてのファイルがアップロードされています")
        print("=" * 80)
        print()
    
    # スキップされたアルバム投稿も確認
    skipped_albums = [
        log for log in logs
        if log.get("upload_type") == "post"
        and len(log.get("target_files", [])) > 1
        and (log.get("upload_status") == "skipped" or log.get("skipped", False))
    ]
    
    if skipped_albums:
        print("=" * 80)
        print(f"【スキップされたアルバム投稿: {len(skipped_albums)}件】")
        print("=" * 80)
        print("（これらは既にアップロード済みのため、スキップされています）")
        print()
    
    print("=" * 80)
    print("分析完了")
    print("=" * 80)
    
    # ファイル数が一致しない投稿がある場合は警告
    if album_info['incomplete_uploads']:
        print(f"\n[WARNING] {len(album_info['incomplete_uploads'])}件のアルバム投稿でファイル数の不一致が見つかりました")
        sys.exit(1)
    else:
        print("\n[OK] すべてのアルバム投稿で、すべてのファイルが適切にアップロードされています")
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
    
    print_report(logs)


if __name__ == "__main__":
    main()

