"""
特定の投稿を直接アップロードするテストスクリプト
"""

import sys
from pathlib import Path
from datetime import datetime

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.database import UploadDatabase
from src.uploader import GoogleBusinessUploader
from src.utils import load_config


def parse_metadata_file(metadata_path: str) -> dict:
    """メタデータファイルを解析"""
    metadata = {
        "post_id": None,
        "taken_at": None,
        "content": "",
    }
    
    with open(metadata_path, "r", encoding="utf-8") as f:
        content = f.read()
        metadata["content"] = content
        
        lines = content.split("\n")
        for line in lines:
            if "投稿ID:" in line:
                # "投稿ID: 3467148003239616465" または "投稿ID:3467148003239616465" の形式に対応
                parts = line.split(":", 1)
                if len(parts) > 1:
                    metadata["post_id"] = parts[1].strip()
            elif "投稿日時:" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    date_str = parts[1].strip()
                    try:
                        metadata["taken_at"] = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
    
    return metadata


def main():
    print("=" * 60)
    print("キャプション付き投稿アップロードテスト")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print(f"  python {sys.argv[0]} <メタデータファイルパス> [location_id]")
        print()
        print("例:")
        print(f'  python {sys.argv[0]} downloads/aburiya_maruko/2024-09-28_15-11/posts/3467148003239616465_metadata.txt')
        print(f'  python {sys.argv[0]} downloads/aburiya_maruko/2024-09-28_15-11/posts/3467148003239616465_metadata.txt 16739471645260047887')
        sys.exit(1)
    
    metadata_path = sys.argv[1]
    metadata_path_obj = Path(metadata_path)
    
    if not metadata_path_obj.exists():
        print(f"[ERROR] メタデータファイルが見つかりません: {metadata_path}")
        sys.exit(1)
    
    # メタデータを解析
    print(f"[INFO] メタデータファイルを読み込み中: {metadata_path}")
    metadata = parse_metadata_file(metadata_path)
    
    if not metadata["post_id"]:
        print("[ERROR] 投稿IDが見つかりません")
        sys.exit(1)
    
    if not metadata["taken_at"]:
        print("[ERROR] 投稿日時が見つかりません")
        sys.exit(1)
    
    post_id = metadata["post_id"]
    taken_at = metadata["taken_at"]
    
    print(f"[INFO] 投稿ID: {post_id}")
    print(f"[INFO] 投稿日時: {taken_at}")
    
    # 画像ファイルを探す
    post_dir = metadata_path_obj.parent
    instagram_id = post_dir.parent.parent.name  # downloads/aburiya_maruko/... -> aburiya_maruko
    
    # 画像ファイルを検索
    image_file = None
    for ext in [".jpg", ".jpeg", ".png"]:
        potential_file = post_dir / f"{instagram_id}_{post_id}{ext}"
        if potential_file.exists():
            image_file = str(potential_file)
            break
    
    if not image_file:
        # 別のパターンで検索
        for file in post_dir.glob(f"*{post_id}.*"):
            if file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                image_file = str(file)
                break
    
    if not image_file:
        print(f"[ERROR] 画像ファイルが見つかりません: {post_dir}")
        sys.exit(1)
    
    print(f"[INFO] 画像ファイル: {image_file}")
    
    # ロケーションIDを取得
    location_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not location_id:
        # config.jsonから取得
        config = load_config("config/config.json")
        companies = config.get("targets", {}).get("companies", [])
        if companies:
            locations = companies[0].get("google_business_locations", [])
            if locations:
                location_id = locations[0].get("location_id")
        
        if not location_id:
            print("[ERROR] ロケーションIDが必要です")
            print("使用方法:")
            print(f"  python {sys.argv[0]} <メタデータファイルパス> <location_id>")
            sys.exit(1)
    
    print(f"[INFO] ロケーションID: {location_id}")
    print()
    
    # データベースを初期化
    db = UploadDatabase("data/upload_history.db")
    
    # 既存の投稿をチェック
    if db.is_post_uploaded(taken_at, instagram_id, location_id, post_id=post_id):
        print(f"[WARNING] この投稿は既にアップロード済みです")
        response = input("削除して再アップロードしますか？ (y/N): ").strip().lower()
        if response == 'y' or response == 'yes':
            # 削除
            import sqlite3
            conn = sqlite3.connect("data/upload_history.db")
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM uploaded_posts WHERE post_id = ? AND instagram_id = ? AND location_id = ?",
                (post_id, instagram_id, location_id)
            )
            conn.commit()
            conn.close()
            print("[OK] アップロード履歴を削除しました")
        else:
            print("[INFO] キャンセルしました")
            sys.exit(0)
    
    # 設定を読み込み
    config = load_config("config/config.json")
    upload_config = config.get("upload", {})
    selenium_config = upload_config.get("selenium", {})
    video_config = upload_config.get("video_conversion", {})
    
    # アップローダーを初期化
    uploader = GoogleBusinessUploader(
        db=db,
        mock_mode=upload_config.get("mock_mode", False),
        mock_delay=0.5,
        location_mapping={},
        video_conversion_enabled=video_config.get("enabled", True),
        video_min_width=video_config.get("min_width", 400),
        video_min_height=video_config.get("min_height", 300),
        use_selenium=selenium_config.get("enabled", False),
        chrome_profile_path=selenium_config.get("chrome_profile_path"),
        profile_name_gbp=selenium_config.get("profile_name_gbp"),
    )
    
    # メタデータを設定
    metadata_dict = {
        "file_path": metadata_path,
        "content": metadata["content"],
    }
    
    print()
    print("=" * 60)
    print("アップロードを開始します")
    print("=" * 60)
    print()
    
    # アップロード実行
    result = uploader.upload_post(
        taken_at=taken_at,
        instagram_id=instagram_id,
        location_id=location_id,
        file_paths=[image_file],
        post_id=post_id,
        metadata=metadata_dict,
    )
    
    print()
    print("=" * 60)
    print("アップロード結果")
    print("=" * 60)
    print()
    
    if result.get("success"):
        print("[OK] アップロード成功！")
        if result.get("caption"):
            print(f"[INFO] キャプション: {result['caption'][:100]}...")
    else:
        print(f"[ERROR] アップロード失敗: {result.get('error', '不明なエラー')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
