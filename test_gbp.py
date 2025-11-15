#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GBP投稿のテスト用スクリプト
使用方法: python test_gbp.py <MODE> <USERNAME> <BUSINESS_ID>
"""

import sys
import subprocess
import os
from datetime import datetime
from pathlib import Path

def check_prerequisites(username, process_id):
    """前提条件のチェック"""
    media_dir = Path("media") / username
    description_file = media_dir / "description" / process_id
    
    print("前提条件のチェック:")
    print(f"  メディアディレクトリ: {media_dir}")
    
    if not media_dir.exists():
        print(f"  ❌ メディアディレクトリが存在しません: {media_dir}")
        return False
    
    media_files = list(media_dir.glob("*.jpg")) + list(media_dir.glob("*.mp4"))
    if not media_files:
        print(f"  ❌ メディアファイルが見つかりません")
        return False
    
    print(f"  ✅ メディアファイル: {len(media_files)}個")
    for f in media_files[:5]:  # 最初の5個だけ表示
        print(f"     - {f.name}")
    
    if description_file.exists():
        print(f"  ✅ 説明文ファイル: {description_file}")
    else:
        print(f"  ⚠️  説明文ファイルが存在しません（オプション）")
    
    return True

def main():
    if len(sys.argv) < 4:
        print("使用方法: python test_gbp.py <MODE> <USERNAME> <BUSINESS_ID>")
        print("例: python test_gbp.py post test_user your_business_id")
        sys.exit(1)
    
    mode = sys.argv[1]
    username = sys.argv[2]
    business_id = sys.argv[3]
    process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if mode not in ["post", "story"]:
        print(f"❌ 無効なモード: {mode} (post または story を指定してください)")
        sys.exit(1)
    
    print(f"テスト開始: モード={mode}, ユーザー名={username}, Business ID={business_id}")
    print("-" * 60)
    
    # 前提条件のチェック
    if not check_prerequisites(username, process_id):
        print("-" * 60)
        print("❌ 前提条件を満たしていません")
        sys.exit(1)
    
    print("-" * 60)
    
    try:
        result = subprocess.run(
            ["python", "postGBP.py", mode, username, business_id, process_id],
            check=False,
            text=True,
            encoding="utf-8"
        )
        
        print("-" * 60)
        if result.returncode == 0:
            print("✅ テスト成功")
        else:
            print(f"❌ テスト失敗（終了コード: {result.returncode}）")
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

