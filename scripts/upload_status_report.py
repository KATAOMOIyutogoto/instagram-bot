"""
アップロード状況レポート
ダウンロードしたファイルのうち、何がアップロードされて何がスキップされたかを確認
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def load_upload_logs(log_file: str = "data/upload_mock_logs.json") -> list[dict]:
    """アップロードログを読み込む"""
    log_path = Path(log_file)
    if not log_path.exists():
        return []
    
    with open(log_path, encoding="utf-8") as f:
        return json.load(f)


def format_datetime(dt_str: str) -> str:
    """日時を読みやすい形式に変換"""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str


def get_file_name(file_path: str) -> str:
    """ファイルパスからファイル名を取得"""
    return Path(file_path).name


def generate_report(logs: list[dict], group_by_execution: bool = True):
    """レポートを生成して表示"""
    if not logs:
        print("アップロードログがありません。")
        return
    
    # 実行日時でグループ化
    if group_by_execution:
        execution_groups = defaultdict(list)
        for log in logs:
            execution_date = log.get("execution_date") or log.get("upload_date", "")
            execution_groups[execution_date].append(log)
        
        # 実行日時でソート（新しい順）
        sorted_executions = sorted(execution_groups.items(), reverse=True)
        
        print("=" * 100)
        print("アップロード状況レポート（実行ごと）")
        print("=" * 100)
        
        for execution_date, execution_logs in sorted_executions:
            print(f"\n【実行日時】 {format_datetime(execution_date)}")
            print("-" * 100)
            
            # Instagram IDでグループ化
            instagram_groups = defaultdict(list)
            for log in execution_logs:
                instagram_id = log.get("instagram_id", "unknown")
                instagram_groups[instagram_id].append(log)
            
            for instagram_id, instagram_logs in sorted(instagram_groups.items()):
                print(f"\n  [Instagram ID] {instagram_id}")
                
                # 投稿とストーリーを分ける
                posts = [log for log in instagram_logs if log.get("upload_type") == "post"]
                stories = [log for log in instagram_logs if log.get("upload_type") == "story"]
                
                # 投稿の統計
                if posts:
                    # upload_statusが"uploaded"または存在しない場合で、skippedがFalseのものをアップロード済みとする
                    uploaded_posts = [p for p in posts if (p.get("upload_status") == "uploaded" or not p.get("upload_status")) and not p.get("skipped")]
                    skipped_posts = [p for p in posts if p.get("skipped") or p.get("upload_status") == "skipped"]
                    failed_posts = [p for p in posts if p.get("upload_status") == "failed"]
                    
                    print(f"    [投稿]")
                    print(f"      [OK] アップロード済み: {len(uploaded_posts)}件")
                    print(f"      [SKIP] スキップ: {len(skipped_posts)}件")
                    print(f"      [NG] 失敗: {len(failed_posts)}件")
                    
                    # アップロード済みの詳細
                    if uploaded_posts:
                        print(f"      【アップロード済み】")
                        for post in uploaded_posts[:5]:  # 最大5件表示
                            taken_at = format_datetime(post.get("taken_at", ""))
                            post_id = post.get("post_id", "N/A")
                            # target_filesがあればそれを使用、なければuploaded_urlsから取得
                            files = post.get("target_files") or post.get("uploaded_urls", [])
                            file_names = [get_file_name(f) for f in files[:3]]  # 最大3ファイル表示
                            print(f"        - {taken_at} (ID: {post_id})")
                            if file_names:
                                print(f"          ファイル: {', '.join(file_names)}")
                    
                    # スキップされたものの詳細
                    if skipped_posts:
                        print(f"      【スキップ】")
                        for post in skipped_posts[:5]:  # 最大5件表示
                            taken_at = format_datetime(post.get("taken_at", ""))
                            post_id = post.get("post_id", "N/A")
                            reason = "重複" if post.get("skipped") else "その他"
                            print(f"        - {taken_at} (ID: {post_id}) - {reason}")
                
                # ストーリーの統計
                if stories:
                    # upload_statusが"uploaded"または存在しない場合で、skippedがFalseのものをアップロード済みとする
                    uploaded_stories = [s for s in stories if (s.get("upload_status") == "uploaded" or not s.get("upload_status")) and not s.get("skipped")]
                    skipped_stories = [s for s in stories if s.get("skipped") or s.get("upload_status") == "skipped"]
                    failed_stories = [s for s in stories if s.get("upload_status") == "failed"]
                    
                    print(f"    [ストーリー]")
                    print(f"      [OK] アップロード済み: {len(uploaded_stories)}件")
                    print(f"      [SKIP] スキップ: {len(skipped_stories)}件")
                    print(f"      [NG] 失敗: {len(failed_stories)}件")
                    
                    # アップロード済みの詳細
                    if uploaded_stories:
                        print(f"      【アップロード済み】")
                        for story in uploaded_stories[:5]:  # 最大5件表示
                            taken_at = format_datetime(story.get("taken_at", ""))
                            story_id = story.get("story_id", "N/A")
                            # target_filesがあればそれを使用、なければuploaded_urlsから取得
                            files = story.get("target_files") or story.get("uploaded_urls", [])
                            file_names = [get_file_name(f) for f in files[:3]]  # 最大3ファイル表示
                            print(f"        - {taken_at} (ID: {story_id})")
                            if file_names:
                                print(f"          ファイル: {', '.join(file_names)}")
                    
                    # スキップされたものの詳細
                    if skipped_stories:
                        print(f"      【スキップ】")
                        for story in skipped_stories[:5]:  # 最大5件表示
                            taken_at = format_datetime(story.get("taken_at", ""))
                            story_id = story.get("story_id", "N/A")
                            reason = "重複" if story.get("skipped") else "その他"
                            print(f"        - {taken_at} (ID: {story_id}) - {reason}")
        
        print("\n" + "=" * 100)
        
        # 全体統計
        total_uploaded = sum(1 for log in logs if (log.get("upload_status") == "uploaded" or not log.get("upload_status")) and not log.get("skipped"))
        total_skipped = sum(1 for log in logs if log.get("skipped") or log.get("upload_status") == "skipped")
        total_failed = sum(1 for log in logs if log.get("upload_status") == "failed")
        
        print(f"\n【全体統計】")
        print(f"  アップロード済み: {total_uploaded}件")
        print(f"  スキップ: {total_skipped}件")
        print(f"  失敗: {total_failed}件")
        print(f"  合計: {len(logs)}件")
    else:
        # グループ化しない場合（シンプルなリスト表示）
        print("=" * 100)
        print("アップロード状況レポート（全件）")
        print("=" * 100)
        
        for i, log in enumerate(logs[:50], 1):  # 最大50件表示
            execution_date = format_datetime(log.get("execution_date") or log.get("upload_date", ""))
            taken_at = format_datetime(log.get("taken_at", ""))
            upload_type = {"post": "投稿", "story": "ストーリー"}.get(log.get("upload_type"), "不明")
            instagram_id = log.get("instagram_id", "unknown")
            status = log.get("upload_status", "unknown")
            skipped = log.get("skipped", False)
            
            status_icon = "[OK]" if status == "uploaded" and not skipped else "[SKIP]" if skipped else "[NG]"
            
            print(f"\n[{i}] {status_icon} {upload_type} - {instagram_id}")
            print(f"    実行日時: {execution_date}")
            print(f"    投稿/ストーリー日時: {taken_at}")
            print(f"    状態: {status} {'(スキップ)' if skipped else ''}")
            
            files = log.get("target_files", [])
            if files:
                print(f"    ファイル: {', '.join([get_file_name(f) for f in files[:3]])}")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="アップロード状況レポート")
    parser.add_argument(
        "--log-file",
        type=str,
        default="data/upload_mock_logs.json",
        help="ログファイルのパス（デフォルト: data/upload_mock_logs.json）",
    )
    parser.add_argument(
        "--instagram-id",
        type=str,
        help="Instagram IDでフィルタ",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="表示件数（デフォルト: 100）",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="シンプルなリスト表示（実行ごとのグループ化なし）",
    )
    
    args = parser.parse_args()
    
    # ログを読み込む
    logs = load_upload_logs(args.log_file)
    
    # フィルタリング
    if args.instagram_id:
        logs = [log for log in logs if log.get("instagram_id") == args.instagram_id]
    
    # 日時でソート（新しい順）
    logs.sort(key=lambda x: x.get("execution_date") or x.get("upload_date", ""), reverse=True)
    
    # 件数制限
    logs = logs[:args.limit]
    
    # レポート生成
    generate_report(logs, group_by_execution=not args.simple)


if __name__ == "__main__":
    main()

