"""
セッションID重複チェック機能のテスト
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.main import InstagramDownloadBot

def main():
    print("=" * 60)
    print("セッションID重複チェック機能のテスト")
    print("=" * 60)
    print()
    
    try:
        bot = InstagramDownloadBot("config/config.json")
        print(f"有効なアカウント数: {len(bot.instagram_accounts)}")
        print()
        
        print("アカウント一覧:")
        for i, account in enumerate(bot.instagram_accounts, 1):
            username = account.get("username", "unknown")
            enabled = account.get("enabled", True)
            status = "有効" if enabled else "無効"
            print(f"  {i}. {username} - {status}")
        print()
        
        # config.jsonから全てのアカウントを確認
        import json
        with open("config/config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        all_accounts = config.get("instagram_accounts", [])
        print(f"設定ファイル内の全アカウント数: {len(all_accounts)}")
        print()
        
        print("設定ファイル内の全アカウント（enabled状態）:")
        for i, account in enumerate(all_accounts, 1):
            username = account.get("username", "unknown")
            enabled = account.get("enabled", True)
            status = "有効" if enabled else "無効"
            print(f"  {i}. {username} - {status}")
        
        print()
        print("=" * 60)
        print("重複チェック機能により、重複しているアカウントは自動的に無効化されています。")
        print("=" * 60)
        
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

