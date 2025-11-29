"""
Google Business Platformへのアップロード機能
モックモードと実際のGoogle Business Profile APIの両方に対応
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import UploadDatabase

logger = logging.getLogger(__name__)

# グローバルなアップロードログビューアー（モックログ用）
_upload_log_viewer = None


def get_upload_log_viewer():
    """アップロードログビューアーのシングルトンインスタンスを取得"""
    global _upload_log_viewer
    if _upload_log_viewer is None:
        from scripts.upload_log_viewer import UploadLogViewer

        _upload_log_viewer = UploadLogViewer()
    return _upload_log_viewer


class GoogleBusinessUploader:
    """Google Business Platformへのアップロードクラス"""

    def __init__(
        self,
        db: UploadDatabase,
        mock_mode: bool = True,
        mock_delay: float = 0.5,
        credentials_path: str | None = None,
        token_path: str | None = None,
        gcs_bucket: str | None = None,
        location_mapping: dict[str, str] | None = None,
        use_direct_upload: bool = True,
    ):
        """
        Args:
            db: アップロード履歴データベース
            mock_mode: モックモード（Trueの場合は実際にはアップロードしない）
            mock_delay: モックアップロード時の遅延時間（秒）
            credentials_path: Google API認証情報ファイルのパス（サービスアカウント用）
            token_path: OAuth2トークンファイルのパス
            gcs_bucket: Google Cloud Storageバケット名（画像アップロード用）
            location_mapping: 店舗IDとGoogle Business ProfileのロケーションIDのマッピング
        """
        self.db = db
        self.mock_mode = mock_mode
        self.mock_delay = mock_delay
        self.gcs_bucket = gcs_bucket
        # location_mapping: 後方互換性のため保持（現在は使用されていない）
        self.location_mapping = location_mapping or {}

        # Google Business Profile API クライアント（モックモードでない場合のみ初期化）
        self.api_client = None
        if not mock_mode:
            try:
                from google_business_api import GoogleBusinessProfileAPI

                self.api_client = GoogleBusinessProfileAPI(
                    credentials_path=credentials_path, token_path=token_path
                )
                logger.info("Google Business Profile API クライアントを初期化しました")
            except ImportError as e:
                logger.error(f"Google Business Profile API の初期化エラー: {e}")
                logger.warning("モックモードにフォールバックします")
                self.mock_mode = True
            except Exception as e:
                logger.error(f"Google Business Profile API の初期化エラー: {e}")
                logger.warning("モックモードにフォールバックします")
                self.mock_mode = True

    def upload_post(
        self,
        taken_at: datetime,
        instagram_id: str,
        location_id: str,
        file_paths: list[str],
        post_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        account_id: str | None = None,  # 後方互換性のため残す（使用しない）
    ) -> dict[str, Any]:
        """
        投稿をアップロード

        Args:
            taken_at: 投稿のアップロード日時
            instagram_id: Instagramのユーザー名またはID
            location_id: Google Business Profile のロケーションID
            file_paths: アップロードするファイルパスのリスト
            post_id: 投稿ID（オプション）
            metadata: メタデータ（オプション）
            account_id: 後方互換性のため残す（使用しない）

        Returns:
            アップロード結果の辞書
        """
        # 重複チェック（日時ベース）
        if self.db.is_post_uploaded(taken_at, instagram_id, location_id):
            logger.info(
                f"投稿は既にアップロード済みです: {taken_at} ({instagram_id}, {location_id})"
            )

            # スキップされた場合もログに記録
            if self.mock_mode:
                try:
                    log_viewer = get_upload_log_viewer()
                    log_viewer.add_upload_log(
                        upload_type="post",
                        taken_at=taken_at,
                        instagram_id=instagram_id,
                        account_id=account_id,
                        location_id=location_id,
                        uploaded_urls=[],
                        caption="",
                        post_id=post_id,
                        metadata=None,
                        target_files=file_paths,
                        skipped=True,
                        upload_status="skipped",
                    )
                except Exception as e:
                    logger.debug(f"スキップログ記録エラー: {e}")

            return {
                "success": True,
                "skipped": True,
                "taken_at": (
                    taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                ),
                "post_id": post_id,
                "account_id": account_id,
                "location_id": location_id,
                "message": "既にアップロード済み",
            }

        try:
            logger.info(
                f"投稿のアップロードを開始: {taken_at} ({instagram_id}, {location_id})"
            )

            # ファイルの存在確認
            missing_files = []
            for file_path in file_paths:
                if not Path(file_path).exists():
                    missing_files.append(file_path)

            if missing_files:
                error_msg = f"ファイルが見つかりません: {', '.join(missing_files)}"
                logger.error(error_msg)
                self.db.record_post_upload(
                    taken_at,
                    instagram_id,
                    location_id,
                    file_paths[0] if file_paths else "",
                    post_id=post_id,
                    upload_status="failed",
                )
                return {
                    "success": False,
                    "taken_at": (
                        taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                    ),
                    "post_id": post_id,
                    "account_id": account_id,
                    "location_id": location_id,
                    "error": error_msg,
                }

            # モックアップロード処理
            if self.mock_mode:
                logger.debug(
                    f"[モック] 投稿をアップロード中: {taken_at} ({account_id}/{location_id})"
                )
                time.sleep(self.mock_delay)  # アップロード処理をシミュレート

                # キャプションを取得
                caption = ""
                if metadata and isinstance(metadata, dict):
                    metadata_content = metadata.get("content", "")
                    if metadata_content:
                        # メタデータからキャプションを抽出
                        # 形式: "--- キャプション ---\nキャプション内容\n\n次のセクション"
                        lines = metadata_content.split("\n")
                        in_caption = False
                        caption_lines = []

                        for line in lines:
                            if "--- キャプション ---" in line:
                                in_caption = True
                                continue
                            if in_caption:
                                # 次のセクション（---で始まる行）が来るまで、すべてをキャプションとして取得
                                # 空行も含めて取得（キャプション内の改行を保持）
                                if line.startswith("---") and "キャプション" not in line:
                                    # 次のセクションが始まった
                                    break
                                else:
                                    # キャプションの一部として追加（空行も含む）
                                    caption_lines.append(line)

                        if caption_lines:
                            # 末尾の空行を削除
                            while caption_lines and not caption_lines[-1].strip():
                                caption_lines.pop()
                            caption = "\n".join(caption_lines).strip()

                # アップロードしたファイルのURLを生成（モック用）
                uploaded_urls = []
                for file_path in file_paths:
                    # ローカルファイルパスをURL形式に変換（モック用）
                    # 実際の実装では、Google Business PlatformのURLが返される
                    file_url = f"file:///{Path(file_path).absolute().as_posix()}"
                    uploaded_urls.append(file_url)

                # モックでは常に成功とする
                upload_result = {
                    "success": True,
                    "taken_at": (
                        taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                    ),
                    "post_id": post_id,
                    "instagram_id": instagram_id,
                    "account_id": account_id,
                    "location_id": location_id,
                    "uploaded_files": file_paths,
                    "uploaded_urls": uploaded_urls,  # アップロードしたファイルのURL
                    "caption": caption,  # キャプション
                    "upload_date": datetime.now().isoformat(),
                    "mock": True,
                    "message": "モックアップロード成功",
                }

                # ログに記録
                logger.info(
                    f"[モックアップロード] 投稿: {taken_at} ({account_id}/{location_id})\n"
                    f"  アップロードURL: {', '.join(uploaded_urls)}\n"
                    f"  キャプション: {caption[:100]}{'...' if len(caption) > 100 else ''}"
                )

                # アップロードログに記録
                try:
                    log_viewer = get_upload_log_viewer()
                    log_viewer.add_upload_log(
                        upload_type="post",
                        taken_at=taken_at,
                        instagram_id=instagram_id,
                        account_id=account_id,
                        location_id=location_id,
                        uploaded_urls=uploaded_urls,
                        caption=caption,
                        post_id=post_id,
                        metadata=metadata,
                        target_files=file_paths,
                        skipped=False,
                        upload_status="uploaded",
                    )
                except Exception as e:
                    logger.debug(f"アップロードログ記録エラー: {e}")

                # アップロード履歴をDBに記録（モックモードでも重複チェックのために必要）
                self.db.record_post_upload(
                    taken_at,
                    instagram_id,
                    location_id,
                    file_paths[0] if file_paths else "",
                    post_id=post_id,
                    upload_status="success",
                    upload_date=datetime.now(),
                )

                logger.info(
                    f"投稿のアップロード完了: {taken_at} ({instagram_id}, {account_id}/{location_id})"
                )
                return upload_result
            else:
                # 実際のGoogle Business Profile API呼び出し
                try:
                    # キャプションを取得
                    caption = ""
                    if metadata and isinstance(metadata, dict):
                        metadata_content = metadata.get("content", "")
                        if metadata_content:
                            lines = metadata_content.split("\n")
                            in_caption = False
                            caption_lines = []

                            for line in lines:
                                if "--- キャプション ---" in line:
                                    in_caption = True
                                    continue
                                if in_caption:
                                    if line.startswith("---") and "キャプション" not in line:
                                        break
                                    else:
                                        caption_lines.append(line)

                            if caption_lines:
                                while caption_lines and not caption_lines[-1].strip():
                                    caption_lines.pop()
                                caption = "\n".join(caption_lines).strip()

                    # 画像・動画をアップロードしてURLを取得
                    media_urls = []
                    for file_path in file_paths:
                        path = Path(file_path)
                        # ファイル拡張子からメディアタイプを判定
                        is_video = path.suffix.lower() in [".mp4", ".mov", ".avi", ".webm", ".mkv"]
                        media_format = "VIDEO" if is_video else "PHOTO"

                        try:
                            if self.use_direct_upload and self.api_client:
                                # 方法1: Google Business Profile APIに直接アップロード（GCS不要）
                                media_url = self.api_client.upload_media_direct(
                                    account_id=account_id,
                                    location_id=location_id,
                                    file_path=file_path,
                                    media_format=media_format,
                                )
                                # メディア情報を辞書形式で保存（URLとフォーマット）
                                media_urls.append({"url": media_url, "format": media_format})
                            elif self.gcs_bucket and self.api_client:
                                # 方法2: GCSにアップロードしてURLを取得
                                media_url = self.api_client.upload_media_to_gcs(
                                    file_path=file_path,
                                    bucket_name=self.gcs_bucket,
                                    object_name=f"{account_id}/{location_id}/{Path(file_path).name}",
                                )
                                # メディア情報を辞書形式で保存（URLとフォーマット）
                                media_urls.append({"url": media_url, "format": media_format})
                        except Exception as e:
                            logger.warning(
                                f"メディア（{'動画' if is_video else '画像'}）のアップロードに失敗: {file_path} - {e}"
                            )
                            # 直接アップロードに失敗した場合、GCSにフォールバック（use_direct_uploadの場合）
                            if self.use_direct_upload and self.gcs_bucket and self.api_client:
                                try:
                                    media_url = self.api_client.upload_media_to_gcs(
                                        file_path=file_path,
                                        bucket_name=self.gcs_bucket,
                                        object_name=f"{account_id}/{location_id}/{Path(file_path).name}",
                                    )
                                    media_urls.append({"url": media_url, "format": media_format})
                                except Exception as gcs_error:
                                    logger.warning(f"GCSアップロードも失敗: {gcs_error}")
                                    # アップロードに失敗しても続行（URLなしで投稿）

                    # Google Business Profile APIで投稿を作成
                    post_result = self.api_client.create_post(
                        account_id=account_id,
                        location_id=location_id,
                        summary=caption,
                        media_urls=media_urls if media_urls else None,
                    )

                    # アップロード結果を構築
                    upload_result = {
                        "success": True,
                        "taken_at": (
                            taken_at.isoformat()
                            if isinstance(taken_at, datetime)
                            else str(taken_at)
                        ),
                        "post_id": post_id,
                        "instagram_id": instagram_id,
                        "account_id": account_id,
                        "location_id": location_id,
                        "uploaded_files": file_paths,
                        "uploaded_urls": media_urls,
                        "caption": caption,
                        "upload_date": datetime.now().isoformat(),
                        "google_post_id": post_result.get("name") if post_result else None,
                        "mock": False,
                        "message": "Google Business Profile API アップロード成功",
                    }

                    logger.info(
                        f"[Google Business Profile API] 投稿を作成: {taken_at} ({account_id}/{location_id})\n"
                        f"  投稿ID: {post_result.get('name') if post_result else 'N/A'}\n"
                        f"  画像URL: {', '.join(str(m) for m in media_urls) if media_urls else 'なし'}\n"
                        f"  キャプション: {caption[:100]}{'...' if len(caption) > 100 else ''}"
                    )

                    # アップロードログに記録（モックモードの場合のみ）
                    if self.mock_mode:
                        try:
                            log_viewer = get_upload_log_viewer()
                            log_viewer.add_upload_log(
                                upload_type="post",
                                taken_at=taken_at,
                                instagram_id=instagram_id,
                                account_id=account_id,
                                location_id=location_id,
                                uploaded_urls=media_urls,
                                caption=caption,
                                post_id=post_id,
                                metadata=metadata,
                                target_files=file_paths,
                                skipped=False,
                                upload_status="uploaded",
                            )
                        except Exception as e:
                            logger.debug(f"アップロードログ記録エラー: {e}")

                except Exception as api_error:
                    logger.error(f"Google Business Profile API エラー: {api_error}")
                    raise

            # アップロード履歴を記録
            self.db.record_post_upload(
                taken_at,
                instagram_id,
                location_id,
                file_paths[0] if file_paths else "",
                post_id=post_id,
                upload_status="success" if upload_result["success"] else "failed",
                upload_date=datetime.now(),
            )

            logger.info(
                f"投稿のアップロード完了: {taken_at} ({instagram_id}, {location_id})"
            )
            return upload_result

        except Exception as e:
            logger.error(
                f"投稿アップロードエラー: {taken_at} ({instagram_id}, {location_id}) - {e}"
            )
            self.db.record_post_upload(
                taken_at,
                instagram_id,
                location_id,
                file_paths[0] if file_paths else "",
                post_id=post_id,
                upload_status="failed",
            )
            return {
                "success": False,
                "taken_at": (
                    taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                ),
                "post_id": post_id,
                "account_id": account_id,
                "location_id": location_id,
                "error": str(e),
            }

    def upload_story(
        self,
        taken_at: datetime,
        instagram_id: str,
        location_id: str,
        file_path: str,
        story_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        account_id: str | None = None,  # 後方互換性のため残す（使用しない）
    ) -> dict[str, Any]:
        """
        ストーリーをアップロード

        Args:
            taken_at: ストーリーのアップロード日時
            instagram_id: Instagramのユーザー名またはID
            location_id: Google Business Profile のロケーションID
            file_path: アップロードするファイルパス
            story_id: ストーリーID（オプション）
            metadata: メタデータ（オプション）
            account_id: 後方互換性のため残す（使用しない）

        Returns:
            アップロード結果の辞書
        """
        # 重複チェック（日時ベース）
        if self.db.is_story_uploaded(taken_at, instagram_id, location_id):
            logger.info(
                f"ストーリーは既にアップロード済みです: {taken_at} ({instagram_id}, {location_id})"
            )

            # スキップされた場合もログに記録
            if self.mock_mode:
                try:
                    log_viewer = get_upload_log_viewer()
                    log_viewer.add_upload_log(
                        upload_type="story",
                        taken_at=taken_at,
                        instagram_id=instagram_id,
                        account_id=account_id,
                        location_id=location_id,
                        uploaded_urls=[],
                        caption="",
                        story_id=story_id,
                        metadata=None,
                        target_files=[file_path],
                        skipped=True,
                        upload_status="skipped",
                    )
                except Exception as e:
                    logger.debug(f"スキップログ記録エラー: {e}")

            return {
                "success": True,
                "skipped": True,
                "taken_at": (
                    taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                ),
                "story_id": story_id,
                "account_id": account_id,
                "location_id": location_id,
                "message": "既にアップロード済み",
            }

        try:
            logger.info(
                f"ストーリーのアップロードを開始: {taken_at} ({instagram_id}, {account_id}/{location_id})"
            )

            # ファイルの存在確認
            if not Path(file_path).exists():
                error_msg = f"ファイルが見つかりません: {file_path}"
                logger.error(error_msg)
                self.db.record_story_upload(
                    taken_at,
                    instagram_id,
                    location_id,
                    file_path,
                    story_id=story_id,
                    upload_status="failed",
                )

                # 失敗した場合もログに記録（モックモードの場合のみ）
                if self.mock_mode:
                    try:
                        log_viewer = get_upload_log_viewer()
                        log_viewer.add_upload_log(
                            upload_type="story",
                            taken_at=taken_at,
                            instagram_id=instagram_id,
                            account_id=account_id,
                            location_id=location_id,
                            uploaded_urls=[],
                            caption="",
                            story_id=story_id,
                            metadata=None,
                            target_files=[file_path],
                            skipped=False,
                            upload_status="failed",
                        )
                    except Exception as e:
                        logger.debug(f"失敗ログ記録エラー: {e}")

                return {
                    "success": False,
                    "taken_at": (
                        taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                    ),
                    "story_id": story_id,
                    "account_id": account_id,
                    "location_id": location_id,
                    "error": error_msg,
                }

            # モックアップロード処理
            if self.mock_mode:
                logger.debug(
                    f"[モック] ストーリーをアップロード中: {taken_at} ({account_id}/{location_id})"
                )
                time.sleep(self.mock_delay)  # アップロード処理をシミュレート

                # アップロードしたファイルのURLを生成（モック用）
                # ローカルファイルパスをURL形式に変換（モック用）
                # 実際の実装では、Google Business PlatformのURLが返される
                file_url = f"file:///{Path(file_path).absolute().as_posix()}"

                # モックでは常に成功とする
                upload_result = {
                    "success": True,
                    "taken_at": (
                        taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                    ),
                    "story_id": story_id,
                    "instagram_id": instagram_id,
                    "account_id": account_id,
                    "location_id": location_id,
                    "uploaded_file": file_path,
                    "uploaded_url": file_url,  # アップロードしたファイルのURL
                    "upload_date": datetime.now().isoformat(),
                    "mock": True,
                    "message": "モックアップロード成功",
                }

                # ログに記録
                logger.info(
                    f"[モックアップロード] ストーリー: {taken_at} ({account_id}/{location_id})\n"
                    f"  アップロードURL: {file_url}"
                )

                # アップロードログに記録
                try:
                    log_viewer = get_upload_log_viewer()
                    log_viewer.add_upload_log(
                        upload_type="story",
                        taken_at=taken_at,
                        instagram_id=instagram_id,
                        account_id=account_id,
                        location_id=location_id,
                        uploaded_urls=[file_url],
                        caption="",  # ストーリーにはキャプションなし
                        story_id=story_id,
                        metadata=metadata,
                        target_files=[file_path],
                        skipped=False,
                        upload_status="uploaded",
                    )
                except Exception as e:
                    logger.debug(f"アップロードログ記録エラー: {e}")

                # アップロード履歴をDBに記録（モックモードでも重複チェックのために必要）
                self.db.record_story_upload(
                    taken_at,
                    instagram_id,
                    location_id,
                    file_path,
                    story_id=story_id,
                    upload_status="success",
                    upload_date=datetime.now(),
                )

                logger.info(
                    f"ストーリーのアップロード完了: {taken_at} ({instagram_id}, {account_id}/{location_id})"
                )
                return upload_result
            else:
                # 実際のGoogle Business Profile API呼び出し
                try:
                    # 画像をアップロードしてURLを取得
                    media_url = None
                    path = Path(file_path)
                    is_video = path.suffix.lower() in [".mp4", ".mov", ".avi", ".webm", ".mkv"]
                    media_format = "VIDEO" if is_video else "PHOTO"

                    if self.use_direct_upload and self.api_client:
                        try:
                            media_url = self.api_client.upload_media_direct(
                                account_id=account_id,
                                location_id=location_id,
                                file_path=file_path,
                                media_format=media_format,
                            )
                        except Exception as e:
                            logger.warning(f"メディアの直接アップロードに失敗: {file_path} - {e}")
                            # 直接アップロードに失敗した場合、GCSにフォールバック
                            if self.gcs_bucket and self.api_client:
                                try:
                                    media_url = self.api_client.upload_media_to_gcs(
                                        file_path=file_path,
                                        bucket_name=self.gcs_bucket,
                                        object_name=f"{account_id}/{location_id}/{Path(file_path).name}",
                                    )
                                except Exception as gcs_error:
                                    logger.warning(f"GCSアップロードも失敗: {gcs_error}")
                    elif self.gcs_bucket and self.api_client:
                        try:
                            media_url = self.api_client.upload_media_to_gcs(
                                file_path=file_path,
                                bucket_name=self.gcs_bucket,
                                object_name=f"{account_id}/{location_id}/{Path(file_path).name}",
                            )
                        except Exception as e:
                            logger.warning(f"画像のGCSアップロードに失敗: {file_path} - {e}")

                    # Google Business Profile APIで投稿を作成（ストーリーは画像のみ）
                    post_result = self.api_client.create_post(
                        account_id=account_id,
                        location_id=location_id,
                        summary="",  # ストーリーにはキャプションなし
                        media_urls=[media_url] if media_url else None,
                    )

                    # アップロード結果を構築
                    upload_result = {
                        "success": True,
                        "taken_at": (
                            taken_at.isoformat()
                            if isinstance(taken_at, datetime)
                            else str(taken_at)
                        ),
                        "story_id": story_id,
                        "instagram_id": instagram_id,
                        "account_id": account_id,
                        "location_id": location_id,
                        "uploaded_file": file_path,
                        "uploaded_url": media_url,
                        "upload_date": datetime.now().isoformat(),
                        "google_post_id": post_result.get("name") if post_result else None,
                        "mock": False,
                        "message": "Google Business Profile API アップロード成功",
                    }

                    logger.info(
                        f"[Google Business Profile API] ストーリーを投稿: {taken_at} ({account_id}/{location_id})\n"
                        f"  投稿ID: {post_result.get('name') if post_result else 'N/A'}\n"
                        f"  画像URL: {media_url if media_url else 'なし'}"
                    )

                    # アップロードログに記録
                    try:
                        log_viewer = get_upload_log_viewer()
                        log_viewer.add_upload_log(
                            upload_type="story",
                            taken_at=taken_at,
                            instagram_id=instagram_id,
                            account_id=account_id,
                            location_id=location_id,
                            uploaded_urls=[media_url] if media_url else [],
                            caption="",  # ストーリーにはキャプションなし
                            story_id=story_id,
                            metadata=metadata,
                        )
                    except Exception as e:
                        logger.debug(f"アップロードログ記録エラー: {e}")

                except Exception as api_error:
                    logger.error(f"Google Business Profile API エラー: {api_error}")
                    raise

            # アップロード履歴を記録
            self.db.record_story_upload(
                taken_at,
                instagram_id,
                location_id,
                file_path,
                story_id=story_id,
                upload_status="success" if upload_result["success"] else "failed",
                upload_date=datetime.now(),
            )

            logger.info(
                f"ストーリーのアップロード完了: {taken_at} ({instagram_id}, {location_id})"
            )
            return upload_result

        except Exception as e:
            logger.error(
                f"ストーリーアップロードエラー: {taken_at} ({instagram_id}, {location_id}) - {e}"
            )
            self.db.record_story_upload(
                taken_at,
                instagram_id,
                location_id,
                file_path,
                story_id=story_id,
                upload_status="failed",
            )
            return {
                "success": False,
                "taken_at": (
                    taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                ),
                "story_id": story_id,
                "account_id": account_id,
                "location_id": location_id,
                "error": str(e),
            }

    def upload_batch_posts(self, posts: list[dict[str, Any]]) -> dict[str, Any]:
        """
        複数の投稿を一括アップロード

        Args:
            posts: 投稿情報のリスト（各要素は post_id, instagram_id, account_id, location_id, file_paths, metadata を含む）

        Returns:
            一括アップロード結果の辞書
        """
        results = {"total": len(posts), "success": 0, "failed": 0, "skipped": 0, "results": []}

        for post in posts:
            # taken_atが必須
            taken_at = post.get("taken_at")
            if not taken_at:
                logger.warning(
                    f"投稿の日時が取得できませんでした: {post.get('post_id', 'unknown')}"
                )
                results["failed"] += 1
                results["results"].append({"success": False, "error": "日時が取得できませんでした"})
                continue

            result = self.upload_post(
                taken_at,
                post.get("instagram_id"),
                post.get("location_id"),
                post.get("file_paths", []),
                post_id=post.get("post_id"),
                metadata=post.get("metadata"),
            )

            results["results"].append(result)

            if result.get("skipped"):
                results["skipped"] += 1
            elif result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(
            f"一括アップロード完了: "
            f"成功 {results['success']}件, "
            f"失敗 {results['failed']}件, "
            f"スキップ {results['skipped']}件"
        )

        return results

    def upload_batch_stories(self, stories: list[dict[str, Any]]) -> dict[str, Any]:
        """
        複数のストーリーを一括アップロード

        Args:
            stories: ストーリー情報のリスト（各要素は story_id, instagram_id, account_id, location_id, file_path, metadata を含む）

        Returns:
            一括アップロード結果の辞書
        """
        results = {"total": len(stories), "success": 0, "failed": 0, "skipped": 0, "results": []}

        for story in stories:
            # taken_atが必須
            taken_at = story.get("taken_at")
            if not taken_at:
                logger.warning(
                    f"ストーリーの日時が取得できませんでした: {story.get('story_id', 'unknown')}"
                )
                results["failed"] += 1
                results["results"].append({"success": False, "error": "日時が取得できませんでした"})
                continue

            result = self.upload_story(
                taken_at,
                story.get("instagram_id"),
                story.get("location_id"),
                story.get("file_path"),
                story_id=story.get("story_id"),
                metadata=story.get("metadata"),
            )

            results["results"].append(result)

            if result.get("skipped"):
                results["skipped"] += 1
            elif result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(
            f"一括アップロード完了: "
            f"成功 {results['success']}件, "
            f"失敗 {results['failed']}件, "
            f"スキップ {results['skipped']}件"
        )

        return results
