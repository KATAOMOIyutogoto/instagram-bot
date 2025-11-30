"""
アップロード管理モジュール
ダウンロード結果をGoogle Business Platformにアップロードする統合機能
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import UploadDatabase
from .uploader import GoogleBusinessUploader

logger = logging.getLogger(__name__)


class UploadManager:
    """アップロード管理クラス"""

    def __init__(
        self,
        db_path: str = "data/upload_history.db",
        mock_mode: bool = True,
        mock_delay: float = 0.5,
        start_date: datetime | None = None,
        location_mapping: dict[str, str] | None = None,
        video_conversion_enabled: bool = True,
        video_min_width: int = 400,
        video_min_height: int = 300,
        use_selenium: bool = False,
        chrome_profile_path: str | None = None,
        profile_name_gbp: str | None = None,
    ):
        """
        Args:
            db_path: データベースファイルのパス
            mock_mode: モックモード（Trueの場合は実際にはアップロードしない）
            mock_delay: モックアップロード時の遅延時間（秒）
            start_date: アップロード開始日時（この日時以降の投稿/ストーリーのみをアップロード）
            location_mapping: Google Business Profileのロケーション情報のマッピング（非推奨、config.jsonで直接設定）
            video_conversion_enabled: 動画変換を有効にするか
            video_min_width: 動画の最小幅
            video_min_height: 動画の最小高さ
            use_selenium: Seleniumを使用してアップロードするか
            chrome_profile_path: Chromeプロファイルのパス（Selenium用）
            profile_name_gbp: GBP用のプロファイル名（Selenium用）
        """
        self.db = UploadDatabase(db_path)
        self.location_mapping = location_mapping or {}
        self.uploader = GoogleBusinessUploader(
            self.db,
            mock_mode=mock_mode,
            mock_delay=mock_delay,
            location_mapping=self.location_mapping,
            video_conversion_enabled=video_conversion_enabled,
            video_min_width=video_min_width,
            video_min_height=video_min_height,
            use_selenium=use_selenium,
            chrome_profile_path=chrome_profile_path,
            profile_name_gbp=profile_name_gbp,
        )

        # アップロード開始日時（この日時以降の投稿/ストーリーのみをアップロード）
        self.start_date = start_date

    def set_location_mapping(self, location_mapping: dict[str, Any]):
        """
        ロケーションマッピングを動的に設定

        Args:
            location_mapping: Google Business Profileのロケーション情報のマッピング（非推奨、config.jsonで直接設定）
        """
        self.location_mapping.update(location_mapping)
        # アップローダーのロケーションマッピングも更新
        self.uploader.location_mapping.update(location_mapping)
        logger.info(f"ロケーションマッピングを更新: {len(location_mapping)}件")

    def process_downloaded_posts(
        self,
        instagram_id: str,
        downloaded_files: list[str],
        locations: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        ダウンロードした投稿を処理してアップロード

        Args:
            instagram_id: Instagramのユーザー名またはID
            downloaded_files: ダウンロードしたファイルパスのリスト
            locations: GBPロケーション情報のリスト [{"account_id": "...", "location_id": "..."}, ...]
                      （Noneの場合はデータベースから取得）

        Returns:
            アップロード結果の辞書
        """
        logger.info(f"投稿のアップロード処理を開始: {instagram_id}")

        # ロケーション情報を取得
        if locations is None:
            locations = self.db.get_locations(instagram_id)
            if not locations:
                logger.warning(f"ロケーション情報が見つかりません: {instagram_id}")
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "results": [],
                    "error": "ロケーション情報が見つかりません",
                }

        # 投稿ファイルとメタデータファイルを分類
        # 投稿の場合は、すべての画像・動画ファイル + キャプションをアップロード
        posts_to_upload = []
        current_post_id = None
        current_post_files = []  # 画像・動画ファイル（すべてのメディア）
        current_metadata_path = None

        # サポートする画像形式
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        # サポートする動画形式
        video_extensions = [".mp4", ".mov", ".avi", ".webm", ".mkv"]

        for file_path in downloaded_files:
            path = Path(file_path)

            # メタデータファイルを検出
            if path.name.endswith("_metadata.txt"):
                # 前の投稿を処理
                if current_post_id and current_post_files:
                    posts_to_upload.append(
                        {
                            "post_id": current_post_id,
                            "instagram_id": instagram_id,
                            "file_paths": current_post_files,  # 画像・動画ファイル（すべてのメディア）
                            "metadata_path": current_metadata_path,
                        }
                    )

                # 新しい投稿の開始
                # メタデータファイル名から投稿IDを抽出（例: 123456789_metadata.txt -> 123456789）
                current_post_id = path.stem.replace("_metadata", "")
                current_post_files = []
                current_metadata_path = str(path)

            # メディアファイル（画像・動画）を検出
            elif path.suffix.lower() in image_extensions + video_extensions:
                # 投稿の場合は画像・動画の両方をアップロード対象とする
                if current_post_id:
                    current_post_files.append(file_path)
                else:
                    # メタデータファイルが見つからない場合、ファイル名から投稿IDを推測
                    # 例: harebare0819_123456789.jpg -> 123456789
                    parts = path.stem.split("_")
                    if len(parts) >= 2:
                        potential_post_id = parts[-1]
                        if potential_post_id.isdigit():
                            current_post_id = potential_post_id
                            current_post_files = [file_path]

        # 最後の投稿を処理
        if current_post_id and current_post_files:
            posts_to_upload.append(
                {
                    "post_id": current_post_id,
                    "instagram_id": instagram_id,
                    "file_paths": current_post_files,
                    "metadata_path": current_metadata_path,
                }
            )

        # メタデータを読み込んで日時を取得
        for post in posts_to_upload:
            if post.get("metadata_path") and Path(post["metadata_path"]).exists():
                try:
                    with open(post["metadata_path"], encoding="utf-8-sig") as f:
                        metadata_content = f.read()
                        post["metadata"] = {
                            "content": metadata_content,
                            "path": post["metadata_path"],
                        }

                    # メタデータから投稿日時を抽出
                    # 形式: "投稿日時: 2024-09-04 02:25:49"
                    taken_at = None
                    for line in metadata_content.split("\n"):
                        if "投稿日時:" in line or "投稿日時：" in line:
                            try:
                                # "投稿日時: 2024-09-04 02:25:49" から日時を抽出
                                date_str = line.split(":", 1)[1].strip()
                                from datetime import datetime

                                taken_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                break
                            except (ValueError, IndexError) as e:
                                logger.debug(f"日時パースエラー: {line} - {e}")
                                continue

                    post["taken_at"] = taken_at
                except Exception as e:
                    logger.warning(f"メタデータ読み込みエラー: {e}")

        # 開始日時でフィルタリング
        if self.start_date:
            original_count = len(posts_to_upload)
            posts_to_upload = [
                post
                for post in posts_to_upload
                if post.get("taken_at") and post["taken_at"] >= self.start_date
            ]
            filtered_count = original_count - len(posts_to_upload)
            if filtered_count > 0:
                logger.info(
                    f"開始日時 ({self.start_date}) 以前の投稿をスキップ: {filtered_count}件"
                )

        # 各ロケーションに対してアップロード
        all_results = {
            "total": len(posts_to_upload) * len(locations),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "results": [],
        }

        for location in locations:
            account_id = location.get("account_id", "")
            location_id = location.get("location_id")
            if not location_id:
                logger.warning(f"ロケーション情報が不完全です（location_idが必要）: {location}")
                continue

            # 各投稿にロケーション情報を設定
            posts_with_location = []
            for post in posts_to_upload:
                # 日時が取得できない場合はスキップ
                if not post.get("taken_at"):
                    logger.warning(
                        f"投稿の日時が取得できませんでした: {post.get('post_id', 'unknown')}"
                    )
                    continue

                post_with_location = post.copy()
                post_with_location["account_id"] = account_id
                post_with_location["location_id"] = location_id
                posts_with_location.append(post_with_location)

            # アップロード実行
            if posts_with_location:
                result = self.uploader.upload_batch_posts(posts_with_location)
                all_results["success"] += result["success"]
                all_results["failed"] += result["failed"]
                all_results["skipped"] += result["skipped"]
                all_results["results"].extend(result["results"])

        logger.info(f"投稿アップロード処理完了: {instagram_id} - {all_results['success']}件成功")
        return all_results

    def process_downloaded_stories(
        self,
        instagram_id: str,
        downloaded_files: list[str],
        locations: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        ダウンロードしたストーリーを処理してアップロード

        Args:
            instagram_id: Instagramのユーザー名またはID
            downloaded_files: ダウンロードしたファイルパスのリスト
            locations: GBPロケーション情報のリスト [{"account_id": "...", "location_id": "..."}, ...]
                      （Noneの場合はデータベースから取得）

        Returns:
            アップロード結果の辞書
        """
        logger.info(f"ストーリーのアップロード処理を開始: {instagram_id}")

        # ロケーション情報を取得
        if locations is None:
            locations = self.db.get_locations(instagram_id)
            if not locations:
                logger.warning(f"ロケーション情報が見つかりません: {instagram_id}")
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "results": [],
                    "error": "ロケーション情報が見つかりません",
                }

        # ストーリーファイルとメタデータファイルを分類
        stories_to_upload = []

        for file_path in downloaded_files:
            path = Path(file_path)

            # メタデータファイルをスキップ（ストーリーのメタデータはオプション）
            if path.name.endswith("_metadata.txt"):
                continue

            # メディアファイル（画像、動画）を検出
            # ストーリーの場合は動画像データのみをアップロード
            if path.suffix.lower() in [".jpg", ".jpeg", ".png", ".mp4", ".mov"]:
                # ファイル名からストーリーIDを抽出
                # 例: 123456789.jpg -> 123456789
                story_id = path.stem

                # メタデータファイルを探す
                metadata_path = path.parent / f"{story_id}_metadata.txt"
                metadata = None
                taken_at = None

                if metadata_path.exists():
                    try:
                        with open(metadata_path, encoding="utf-8-sig") as f:
                            metadata_content = f.read()
                            metadata = {"content": metadata_content, "path": str(metadata_path)}

                        # メタデータからストーリー日時を抽出
                        # 形式: "投稿日時: 2024-09-04 02:25:49"
                        for line in metadata_content.split("\n"):
                            if "投稿日時:" in line or "投稿日時：" in line:
                                try:
                                    # "投稿日時: 2024-09-04 02:25:49" から日時を抽出
                                    date_str = line.split(":", 1)[1].strip()
                                    from datetime import datetime

                                    taken_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                    break
                                except (ValueError, IndexError) as e:
                                    logger.debug(f"日時パースエラー: {line} - {e}")
                                    continue
                    except Exception as e:
                        logger.warning(f"メタデータ読み込みエラー: {e}")

                # 日時が取得できない場合はスキップ
                if not taken_at:
                    logger.warning(f"ストーリーの日時が取得できませんでした: {story_id}")
                    continue

                # 開始日時でフィルタリング
                if self.start_date and taken_at < self.start_date:
                    logger.debug(
                        f"開始日時 ({self.start_date}) 以前のストーリーをスキップ: {story_id} ({taken_at})"
                    )
                    continue

                # ストーリーの場合は動画像データのみをアップロード対象とする
                stories_to_upload.append(
                    {
                        "story_id": story_id,
                        "instagram_id": instagram_id,
                        "file_path": str(path),
                        "taken_at": taken_at,
                        "metadata": metadata,
                    }
                )

        # 各ロケーションに対してアップロード
        all_results = {
            "total": len(stories_to_upload) * len(locations),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "results": [],
        }

        for location in locations:
            account_id = location.get("account_id", "")
            location_id = location.get("location_id")
            if not location_id:
                logger.warning(f"ロケーション情報が不完全です（location_idが必要）: {location}")
                continue

            # 各ストーリーにロケーション情報を設定
            stories_with_location = []
            for story in stories_to_upload:
                story_with_location = story.copy()
                story_with_location["account_id"] = account_id
                story_with_location["location_id"] = location_id
                stories_with_location.append(story_with_location)

            # アップロード実行
            if stories_with_location:
                result = self.uploader.upload_batch_stories(stories_with_location)
                all_results["success"] += result["success"]
                all_results["failed"] += result["failed"]
                all_results["skipped"] += result["skipped"]
                all_results["results"].extend(result["results"])

        logger.info(
            f"ストーリーアップロード処理完了: {instagram_id} - {all_results['success']}件成功"
        )
        return all_results

    def get_upload_statistics(self) -> dict[str, Any]:
        """
        アップロード統計情報を取得

        Returns:
            統計情報の辞書
        """
        return self.db.get_upload_statistics()

    def get_upload_history(
        self,
        instagram_id: str | None = None,
        account_id: str | None = None,
        location_id: str | None = None,
        content_type: str = "all",
    ) -> dict[str, list[dict[str, Any]]]:
        """
        アップロード履歴を取得

        Args:
            instagram_id: Instagramのユーザー名またはID（Noneの場合は全ユーザー）
            account_id: Google Business Profile のアカウントID（Noneの場合は全アカウント）
            location_id: Google Business Profile のロケーションID（Noneの場合は全ロケーション）
            content_type: コンテンツタイプ ('posts', 'stories', 'all')

        Returns:
            アップロード履歴の辞書
        """
        history = {}

        if content_type in ["posts", "all"]:
            history["posts"] = self.db.get_uploaded_posts(instagram_id, location_id)

        if content_type in ["stories", "all"]:
            history["stories"] = self.db.get_uploaded_stories(instagram_id, location_id)

        return history

    # 後方互換性のためのメソッド（非推奨）
    def add_store_mapping(
        self, instagram_id: str, store_id: str, store_name: str | None = None
    ) -> bool:
        """
        後方互換性のためのメソッド（非推奨）
        ロケーション情報はconfig.jsonで直接設定してください。
        """
        logger.warning(
            "add_store_mappingは非推奨です。ロケーション情報はconfig.jsonで直接設定してください。"
        )
        return False

    def get_store_mappings(self) -> list[dict[str, Any]]:
        """
        すべてのインスタIDと店舗IDのマッピングを取得

        Returns:
            マッピング情報のリスト
        """
        return self.db.get_all_mappings()
