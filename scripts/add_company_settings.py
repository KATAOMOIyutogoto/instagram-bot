"""
企業ごとのストーリー・投稿連携設定を追加するスクリプト
config.jsonの各企業設定に、download_posts, download_stories, upload_posts, upload_storiesを追加します
"""

import json
import sys
from pathlib import Path

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.utils import load_config, save_config


def add_company_settings(
    config_path: str = "config/config.json",
    default_download_posts: bool = True,
    default_download_stories: bool = True,
    default_upload_posts: bool = True,
    default_upload_stories: bool = True,
    force_update: bool = False,
):
    """
    企業ごとの設定を追加
    
    Args:
        config_path: 設定ファイルのパス
        default_download_posts: デフォルトの投稿ダウンロード設定
        default_download_stories: デフォルトのストーリーダウンロード設定
        default_upload_posts: デフォルトの投稿アップロード設定
        default_upload_stories: デフォルトのストーリーアップロード設定
        force_update: Trueの場合、既存の設定も上書きする
    """
    config = load_config(config_path)
    
    if "targets" not in config or "companies" not in config["targets"]:
        print("[ERROR] targets.companiesが見つかりません")
        return False
    
    companies = config["targets"]["companies"]
    updated_count = 0
    
    for company in companies:
        if not isinstance(company, dict):
            continue
        
        # 既存の設定を確認
        has_download_posts = "download_posts" in company
        has_download_stories = "download_stories" in company
        has_upload_posts = "upload_posts" in company
        has_upload_stories = "upload_stories" in company
        
        # 設定を追加（既存の設定がない場合、またはforce_updateがTrueの場合）
        if not has_download_posts or force_update:
            company["download_posts"] = default_download_posts
            updated_count += 1
        
        if not has_download_stories or force_update:
            company["download_stories"] = default_download_stories
            updated_count += 1
        
        if not has_upload_posts or force_update:
            company["upload_posts"] = default_upload_posts
            updated_count += 1
        
        if not has_upload_stories or force_update:
            company["upload_stories"] = default_upload_stories
            updated_count += 1
    
    # 設定を保存
    save_config(config, config_path)
    
    print(f"[OK] {len(companies)}社の企業設定を確認しました")
    print(f"[OK] {updated_count}件の設定項目を追加/更新しました")
    
    return True


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="企業ごとのストーリー・投稿連携設定を追加"
    )
    parser.add_argument(
        "--config",
        default="config/config.json",
        help="設定ファイルのパス（デフォルト: config/config.json）",
    )
    parser.add_argument(
        "--download-posts",
        type=bool,
        default=True,
        help="デフォルトの投稿ダウンロード設定（デフォルト: True）",
    )
    parser.add_argument(
        "--download-stories",
        type=bool,
        default=True,
        help="デフォルトのストーリーダウンロード設定（デフォルト: True）",
    )
    parser.add_argument(
        "--upload-posts",
        type=bool,
        default=True,
        help="デフォルトの投稿アップロード設定（デフォルト: True）",
    )
    parser.add_argument(
        "--upload-stories",
        type=bool,
        default=True,
        help="デフォルトのストーリーアップロード設定（デフォルト: True）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存の設定も上書きする",
    )
    
    args = parser.parse_args()
    
    # bool型の引数を正しく処理（文字列の場合は変換）
    def str_to_bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ("yes", "true", "t", "1"):
            return True
        elif v.lower() in ("no", "false", "f", "0"):
            return False
        else:
            raise argparse.ArgumentTypeError("Boolean value expected.")
    
    download_posts = str_to_bool(args.download_posts) if isinstance(args.download_posts, str) else args.download_posts
    download_stories = str_to_bool(args.download_stories) if isinstance(args.download_stories, str) else args.download_stories
    upload_posts = str_to_bool(args.upload_posts) if isinstance(args.upload_posts, str) else args.upload_posts
    upload_stories = str_to_bool(args.upload_stories) if isinstance(args.upload_stories, str) else args.upload_stories
    
    print("=" * 60)
    print("企業ごとのストーリー・投稿連携設定を追加")
    print("=" * 60)
    print()
    print(f"設定ファイル: {args.config}")
    print(f"デフォルト設定:")
    print(f"  - download_posts: {download_posts}")
    print(f"  - download_stories: {download_stories}")
    print(f"  - upload_posts: {upload_posts}")
    print(f"  - upload_stories: {upload_stories}")
    print(f"  - force_update: {args.force}")
    print()
    
    if add_company_settings(
        config_path=args.config,
        default_download_posts=download_posts,
        default_download_stories=download_stories,
        default_upload_posts=upload_posts,
        default_upload_stories=upload_stories,
        force_update=args.force,
    ):
        print()
        print("=" * 60)
        print("[OK] 設定の追加が完了しました")
        print("=" * 60)
        print()
        print("注意:")
        print("  各企業の設定は必要に応じて手動で編集してください。")
        print("  例: ストーリーのみ連携する場合")
        print('    "download_posts": false,')
        print('    "download_stories": true,')
        print('    "upload_posts": false,')
        print('    "upload_stories": true')
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("[ERROR] 設定の追加に失敗しました")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

