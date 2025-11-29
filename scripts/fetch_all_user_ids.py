"""
config.json内の全てのInstagramアカウントのユーザーIDを取得して保存するスクリプト
1回だけ実行する用
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.instagram_bot import InstagramBot
from src.utils import load_config, save_config

logger = None


def fetch_all_user_ids(config_path: str = "config/config.json", delay: float = 3.0):
    """
    config.json内の全てのInstagramアカウントのユーザーIDを取得して保存

    Args:
        config_path: 設定ファイルのパス
        delay: 各アカウント間の待機時間（秒）
    """
    # ログ設定
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    global logger
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("InstagramユーザーID取得スクリプトを開始")
    logger.info("=" * 60)

    # 設定ファイルを読み込む
    config = load_config(config_path)
    logger.info(f"設定ファイルを読み込みました: {config_path}")

    # Instagram認証情報を取得
    instagram_config = config.get("instagram", {})
    username = instagram_config.get("username")
    password = instagram_config.get("password")
    session_file = instagram_config.get("session_file", "data/session.json")

    if not username or not password:
        logger.error("Instagramの認証情報が設定されていません")
        logger.error("config.jsonの'instagram'セクションに'username'と'password'を設定してください")
        return False

    # InstagramBotを初期化
    logger.info("Instagram Botを初期化しています...")
    bot = InstagramBot(username, password, session_file)

    # ログイン
    if not bot.login():
        logger.error("ログインに失敗しました")
        return False

    logger.info("ログインに成功しました")

    # 企業リストを取得
    companies_config = config.get("targets", {}).get("companies", [])
    if not companies_config:
        logger.error("企業リストが設定されていません")
        return False

    logger.info(f"処理対象: {len(companies_config)}社")

    # 各企業のユーザーIDを取得
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for idx, company in enumerate(companies_config, 1):
        instagram_id = company.get("instagram_id")
        if not instagram_id:
            logger.warning(f"[{idx}/{len(companies_config)}] instagram_idが設定されていません: {company}")
            error_count += 1
            continue

        # 既にuser_idが設定されているか確認
        existing_user_id = company.get("user_id")
        if existing_user_id:
            logger.info(f"[{idx}/{len(companies_config)}] スキップ: {instagram_id} (既にuser_idが設定されています: {existing_user_id})")
            skipped_count += 1
            continue

        logger.info(f"[{idx}/{len(companies_config)}] 処理中: {instagram_id}")

        # 数値のみの場合は既にユーザーIDと判断
        if instagram_id.isdigit():
            logger.info(f"  ユーザーIDとして認識: {instagram_id}")
            company["user_id"] = instagram_id
            updated_count += 1
        else:
            # ユーザーIDを取得
            try:
                # 待機時間を設ける（レート制限対策）
                if idx > 1:  # 最初のアカウント以外は待機
                    time.sleep(delay)

                user_id = bot.get_user_id(instagram_id, delay=0)  # 既に待機時間を設けているのでdelay=0

                if user_id:
                    company["user_id"] = user_id
                    logger.info(f"  ✓ ユーザーIDを取得しました: {instagram_id} -> {user_id}")
                    updated_count += 1
                else:
                    logger.error(f"  ✗ ユーザーIDの取得に失敗しました: {instagram_id}")
                    error_count += 1
            except Exception as e:
                logger.error(f"  ✗ エラー: {instagram_id} - {e}")
                error_count += 1

        # 定期的にconfig.jsonを保存（10社ごと）
        if idx % 10 == 0:
            try:
                save_config(config, config_path)
                logger.info(f"  中間保存: {idx}社処理完了")
            except Exception as e:
                logger.warning(f"  中間保存エラー: {e}")

    # 最終保存
    try:
        save_config(config, config_path)
        logger.info("設定ファイルを保存しました")
    except Exception as e:
        logger.error(f"設定ファイルの保存エラー: {e}")
        return False

    # 結果サマリー
    logger.info("=" * 60)
    logger.info("処理完了")
    logger.info("=" * 60)
    logger.info(f"更新: {updated_count}社")
    logger.info(f"スキップ: {skipped_count}社（既にuser_idが設定済み）")
    logger.info(f"エラー: {error_count}社")
    logger.info(f"合計: {len(companies_config)}社")

    return error_count == 0


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="InstagramユーザーID取得スクリプト")
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.json",
        help="設定ファイルのパス（デフォルト: config/config.json）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="各アカウント間の待機時間（秒、デフォルト: 3.0）",
    )

    args = parser.parse_args()

    try:
        success = fetch_all_user_ids(args.config, args.delay)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("ユーザーによって中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

