#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ストーリー取得のテスト用スクリプト
使用方法: python test_story.py <USERNAME>
"""

import sys
import subprocess
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("使用方法: python test_story.py <USERNAME>")
        print("例: python test_story.py test_user")
        sys.exit(1)
    
    username = sys.argv[1]
    process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"テスト開始: ユーザー名={username}, プロセスID={process_id}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            ["python", "story.py", username, process_id],
            check=False,
            text=True,
            encoding="utf-8"
        )
        
        print("-" * 60)
        if result.returncode == 0:
            print("✅ テスト成功")
        elif result.returncode == 1:
            print("⚠️  テスト完了（エラーまたはスキップ）")
        elif result.returncode == 3:
            print("🔒 アカウントロック検出")
        else:
            print(f"❌ テスト失敗（終了コード: {result.returncode}）")
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

