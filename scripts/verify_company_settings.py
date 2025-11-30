"""
企業ごとの設定を確認するスクリプト
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.utils import load_config


def verify_settings(config_path: str = "config/config.json"):
    """設定を確認"""
    config = load_config(config_path)
    
    companies = config["targets"]["companies"]
    
    stats = defaultdict(int)
    v2_companies = []
    v3_companies = []
    default_companies = []
    
    for company in companies:
        if not isinstance(company, dict):
            continue
        
        instagram_id = company.get("instagram_id")
        download_posts = company.get("download_posts", True)
        download_stories = company.get("download_stories", True)
        upload_posts = company.get("upload_posts", True)
        upload_stories = company.get("upload_stories", True)
        
        # v2: 投稿のみ（download_stories: false, upload_stories: false）
        if download_stories == False and upload_stories == False:
            stats["v2"] += 1
            v2_companies.append(instagram_id)
        # v3: ストーリー+投稿（すべてtrue）
        elif download_posts == True and download_stories == True and upload_posts == True and upload_stories == True:
            stats["v3"] += 1
            v3_companies.append(instagram_id)
        else:
            stats["other"] += 1
            default_companies.append((instagram_id, download_posts, download_stories, upload_posts, upload_stories))
    
    print("=" * 60)
    print("企業ごとの設定確認結果")
    print("=" * 60)
    print()
    print(f"総企業数: {len(companies)}社")
    print()
    print(f"v2（投稿のみ）: {stats['v2']}社")
    print(f"v3（ストーリー+投稿）: {stats['v3']}社")
    print(f"その他: {stats['other']}社")
    print()
    
    if default_companies:
        print("設定が標準的でない企業:")
        for insta_id, dp, ds, up, us in default_companies[:10]:
            print(f"  - {insta_id}: download_posts={dp}, download_stories={ds}, upload_posts={up}, upload_stories={us}")
        if len(default_companies) > 10:
            print(f"  ... 他 {len(default_companies) - 10}件")
        print()
    
    return stats


if __name__ == "__main__":
    verify_settings()

