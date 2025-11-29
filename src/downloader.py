"""
Instagramのストーリーと投稿のダウンロード機能
"""

import logging
import time
from typing import Any

from instagrapi import Client
from instagrapi.exceptions import ClientError

from .utils import get_download_path

logger = logging.getLogger(__name__)


class InstagramDownloader:
    """Instagramコンテンツのダウンローダー"""

    def __init__(
        self,
        client: Client,
        base_directory: str = "downloads",
        organize_by_company: bool = True,
        organize_by_date: bool = True,
        delay_between_requests: float = 2.0,
    ):
        """
        Args:
            client: instagrapiのClientインスタンス
            base_directory: ダウンロード先のベースディレクトリ
            organize_by_company: 企業ごとにフォルダ分けするか
            organize_by_date: 日付ごとにフォルダ分けするか
            delay_between_requests: リクエスト間の待機時間（秒）
        """
        self.client = client
        self.base_directory = base_directory
        self.organize_by_company = organize_by_company
        self.organize_by_date = organize_by_date
        self.delay_between_requests = delay_between_requests

    def _create_media_from_raw_item(self, item: dict[str, Any], media_pk: str) -> Any | None:
        """
        生のAPIレスポンスアイテムからMediaオブジェクトを作成（簡易版）

        Args:
            item: 生のAPIレスポンスアイテム
            media_pk: メディアのPK

        Returns:
            Mediaオブジェクト（簡易版）またはNone
        """
        try:
            # 簡易的なMediaオブジェクトを作成
            # instagrapiのMediaクラスの代わりに、必要な属性を持つオブジェクトを作成
            from datetime import datetime
            from types import SimpleNamespace

            media_type = item.get("media_type", 1)  # 1=Photo, 2=Video, 8=Album
            taken_at = item.get("taken_at", 0)
            if isinstance(taken_at, (int, float)):
                taken_at = datetime.fromtimestamp(taken_at)

            # 簡易Mediaオブジェクトを作成
            media = SimpleNamespace()
            media.pk = media_pk
            media.media_type = media_type
            media.taken_at = taken_at
            media.like_count = item.get("like_count", 0)
            media.comment_count = item.get("comment_count", 0)
            media.caption_text = ""
            if item.get("caption"):
                caption = item.get("caption")
                if isinstance(caption, dict):
                    media.caption_text = caption.get("text", "")
                else:
                    media.caption_text = str(caption)
            media.caption = media.caption_text

            # 生データを保持（後でダウンロードURLを抽出するため）
            media._raw_item = item

            return media
        except Exception as e:
            logger.debug(f"生データからのMediaオブジェクト作成エラー: {e}")
            return None

    def _extract_download_urls_from_raw_item(
        self, item: dict[str, Any], media_type: int
    ) -> list[str]:
        """
        生のAPIレスポンスアイテムからダウンロードURLを抽出

        Args:
            item: 生のAPIレスポンスアイテム
            media_type: メディアタイプ（1=Photo, 2=Video, 8=Album）

        Returns:
            ダウンロードURLのリスト
        """
        urls = []
        try:
            if media_type == 1:  # Photo
                # image_versions2から最高解像度の画像URLを取得
                if item.get("image_versions2"):
                    candidates = item["image_versions2"].get("candidates", [])
                    if candidates:
                        # 最高解像度の画像を取得（最初の候補が通常最高解像度）
                        urls.append(candidates[0].get("url", ""))
            elif media_type == 2:  # Video
                # video_versionsから最高解像度の動画URLを取得
                if item.get("video_versions"):
                    video_versions = item["video_versions"]
                    if video_versions:
                        # 最高解像度の動画を取得（最初の候補が通常最高解像度）
                        urls.append(video_versions[0].get("url", ""))
            elif media_type == 8:  # Album
                # carousel_mediaから各メディアのURLを取得
                if item.get("carousel_media"):
                    carousel_items = item["carousel_media"]
                    for carousel_item in carousel_items:
                        carousel_media_type = carousel_item.get("media_type", 1)
                        if carousel_media_type == 1:  # Photo
                            if carousel_item.get("image_versions2"):
                                candidates = carousel_item["image_versions2"].get("candidates", [])
                                if candidates:
                                    urls.append(candidates[0].get("url", ""))
                        elif carousel_media_type == 2:  # Video
                            if carousel_item.get("video_versions"):
                                video_versions = carousel_item["video_versions"]
                                if video_versions:
                                    urls.append(video_versions[0].get("url", ""))
        except Exception as e:
            logger.debug(f"ダウンロードURL抽出エラー: {e}")

        # 空のURLを除外
        urls = [url for url in urls if url]
        return urls

    def download_posts(
        self, username: str, user_id: str, limit: int = 20, retry_attempts: int = 3
    ) -> list[str] | dict:
        """
        投稿をダウンロード

        Args:
            username: ユーザー名
            user_id: ユーザーID
            limit: ダウンロードする投稿数
            retry_attempts: リトライ回数

        Returns:
            ダウンロードしたファイルのパスリスト
        """
        downloaded_files = []
        rate_limit_detected = False  # レート制限エラーを追跡

        try:
            logger.info(f"投稿のダウンロードを開始: {username} (最大{limit}件)")

            # メディアを取得（エラーハンドリング付き、複数の方法を試す）
            medias = []
            last_error = None

            # 方法1: user_medias_v1を直接試す（Private API）
            try:
                logger.debug("user_medias_v1を試します...")
                medias = self.client.user_medias_v1(user_id, amount=limit)
                if medias:
                    logger.info(f"user_medias_v1で{len(medias)}件の投稿を取得しました")
                    last_error = None  # 成功したのでエラーをクリア
                else:
                    logger.warning("user_medias_v1で投稿が0件でした")
            except Exception as v1_error:
                last_error = v1_error
                error_str = str(v1_error).lower()
                logger.warning(f"user_medias_v1でエラーが発生しました: {v1_error}")

            # 方法2: 生のAPIレスポンスを直接取得してバリデーションを回避（方法1が失敗した場合）
            if not medias:
                try:
                    logger.info("生のAPIレスポンスを直接取得します...")
                    # private APIを使って直接リクエスト
                    # instagrapiの内部実装を参考に、正しいエンドポイントを使用
                    try:
                        # 方法A: private.request()を使用（完全なURLを指定）
                        response_obj = self.client.private.request(
                            "GET",
                            f"https://i.instagram.com/api/v1/feed/user/{user_id}/",
                            params={
                                "max_id": "",
                                "count": limit,
                                "rank_token": (
                                    f"{self.client.user_id}_{self.client.rank_token}"
                                    if hasattr(self.client, "rank_token")
                                    else ""
                                ),
                            },
                        )
                        # ResponseオブジェクトからJSONを取得
                        if hasattr(response_obj, "json"):
                            response = response_obj.json()
                        elif hasattr(response_obj, "text"):
                            import json

                            response = json.loads(response_obj.text)
                        else:
                            response = response_obj
                    except Exception as request_error:
                        # 方法B: requestsライブラリを直接使用（instagrapiのセッション情報を利用）
                        try:
                            import requests

                            # instagrapiのセッション情報を取得
                            session = self.client.private
                            url = f"https://i.instagram.com/api/v1/feed/user/{user_id}/"
                            params = {"max_id": "", "count": limit}

                            # セッションのヘッダーとクッキーを取得
                            headers = dict(session.headers) if hasattr(session, "headers") else {}
                            cookies = dict(session.cookies) if hasattr(session, "cookies") else {}

                            response_obj = requests.get(
                                url, params=params, headers=headers, cookies=cookies, timeout=30
                            )
                            response_obj.raise_for_status()
                            response = response_obj.json()
                        except Exception as requests_error:
                            logger.debug(f"requests直接呼び出しも失敗: {requests_error}")
                            raise request_error

                    if response and response.get("status") == "ok" and response.get("items"):
                        items = response.get("items", [])
                        logger.info(
                            f"生のAPIレスポンスから{len(items)}件の投稿アイテムを取得しました"
                        )

                        # 各アイテムからmedia_pkを抽出して、個別にmedia_infoで取得
                        medias = []
                        for item in items[:limit]:
                            try:
                                media_pk = item.get("pk") or item.get("id")
                                if not media_pk:
                                    continue

                                # media_infoで個別に取得（バリデーションエラーを回避するため）
                                try:
                                    media = self.client.media_info(media_pk)
                                    if media:
                                        medias.append(media)
                                        logger.debug(f"media_infoで投稿を取得: {media_pk}")
                                except Exception as media_info_error:
                                    error_str = str(media_info_error).lower()
                                    # バリデーションエラーでも続行（生データから直接ダウンロードを試みる）
                                    if "validation" in error_str or "pydantic" in error_str:
                                        logger.debug(
                                            f"media_infoでバリデーションエラー、生データから直接ダウンロードを試みます: {media_pk}"
                                        )
                                        # 生データから直接ダウンロードURLを抽出してダウンロード
                                        try:
                                            # 生のアイテムデータから直接メディア情報を抽出
                                            raw_media = self._create_media_from_raw_item(
                                                item, media_pk
                                            )
                                            if raw_media:
                                                medias.append(raw_media)
                                                logger.info(f"生データから投稿を取得: {media_pk}")
                                        except Exception as raw_media_error:
                                            logger.debug(
                                                f"生データからの投稿取得も失敗: {raw_media_error}"
                                            )
                                    else:
                                        logger.warning(
                                            f"media_infoでエラー: {media_pk} - {media_info_error}"
                                        )
                            except Exception as item_error:
                                logger.debug(f"アイテム処理エラー: {item_error}")
                                continue

                        if medias:
                            logger.info(
                                f"生のAPIレスポンスから{len(medias)}件の投稿を正常に取得しました"
                            )
                            last_error = None
                        else:
                            logger.warning("生のAPIレスポンスから投稿を取得できませんでした")
                    else:
                        logger.warning(
                            f"生のAPIレスポンスが無効: status={response.get('status') if response else 'None'}"
                        )
                except Exception as raw_error:
                    last_error = raw_error
                    error_str = str(raw_error).lower()
                    if "validation" not in error_str and "pydantic" not in error_str:
                        logger.warning(
                            f"生のAPIレスポンス取得でもエラーが発生しました: {raw_error}"
                        )

            # すべての方法が失敗した場合
            if not medias:
                if last_error:
                    error_str = str(last_error).lower()
                    # バリデーションエラーやデータエラーの場合は警告のみ
                    if (
                        "validation" in error_str
                        or "pydantic" in error_str
                        or "data" in error_str
                        or "jsondecode" in error_str
                    ):
                        logger.warning(
                            f"すべての方法で投稿取得に失敗しました（バリデーションエラーの可能性）: {last_error}"
                        )
                    else:
                        logger.error(f"すべての方法で投稿取得に失敗しました: {last_error}")
                logger.info(f"投稿の取得をスキップします: {username} (user_id: {user_id})")

            # 各投稿をダウンロード
            for idx, media in enumerate(medias, 1):
                try:
                    logger.info(f"[{idx}/{len(medias)}] 投稿をダウンロード中: {media.pk}")

                    # 投稿のアップロード日時を取得
                    from datetime import datetime

                    taken_at = None
                    if hasattr(media, "taken_at") and media.taken_at:
                        if isinstance(media.taken_at, (int, float)):
                            taken_at = datetime.fromtimestamp(media.taken_at)
                        else:
                            taken_at = media.taken_at

                    # 各投稿のアップロード日時でフォルダを作成
                    download_path = get_download_path(
                        self.base_directory,
                        username,
                        "posts",
                        self.organize_by_company,
                        self.organize_by_date,
                        taken_at,
                    )

                    # リトライロジック
                    post_files = []  # この投稿でダウンロードしたファイル
                    for attempt in range(retry_attempts):
                        try:
                            # 生データから作成したMediaオブジェクトの場合は、生データから直接ダウンロード
                            if hasattr(media, "_raw_item") and media._raw_item:
                                # 生データから直接ダウンロードURLを抽出
                                download_urls = self._extract_download_urls_from_raw_item(
                                    media._raw_item, media.media_type
                                )
                                if download_urls:
                                    import requests

                                    headers = {
                                        "User-Agent": self.client.private.headers.get(
                                            "User-Agent", "Mozilla/5.0"
                                        ),
                                    }

                                    for url_idx, download_url in enumerate(download_urls):
                                        try:
                                            response = requests.get(
                                                download_url, headers=headers, timeout=30
                                            )
                                            response.raise_for_status()

                                            # ファイル拡張子を判定
                                            if media.media_type == 2:  # Video
                                                ext = ".mp4"
                                            else:  # Photo
                                                ext = ".jpg"

                                            filename = (
                                                f"{media.pk}_{url_idx}{ext}"
                                                if len(download_urls) > 1
                                                else f"{media.pk}{ext}"
                                            )
                                            file_path = download_path / filename

                                            with open(file_path, "wb") as f:
                                                f.write(response.content)

                                            post_files.append(str(file_path))
                                            logger.info(
                                                f"生データから直接ダウンロード完了: {file_path}"
                                            )
                                        except Exception as url_download_error:
                                            logger.warning(
                                                f"URLからのダウンロードエラー: {url_download_error}"
                                            )
                                            continue

                                    # 生データから直接ダウンロードした場合でも、メタデータ保存処理は後で実行される
                                    # breakはしない（メタデータ保存処理を実行するため）
                                else:
                                    logger.warning(
                                        f"生データからダウンロードURLを抽出できませんでした: {media.pk}"
                                    )

                            # 通常のMediaオブジェクトの場合は、通常のダウンロード方法を使用
                            if not post_files:
                                if media.media_type == 1:  # Photo
                                    file_path = self.client.photo_download(
                                        media.pk, folder=str(download_path)
                                    )
                                    if file_path:
                                        post_files.append(str(file_path))
                                        logger.info(f"画像ダウンロード完了: {file_path}")
                                elif media.media_type == 2:  # Video
                                    file_path = self.client.video_download(
                                        media.pk, folder=str(download_path)
                                    )
                                    if file_path:
                                        post_files.append(str(file_path))
                                        logger.info(f"動画ダウンロード完了: {file_path}")
                                elif media.media_type == 8:  # Album (複数画像/動画)
                                    # アルバムの場合は全てのリソースをダウンロード
                                    album_files = self.client.album_download(
                                        media.pk, folder=str(download_path)
                                    )
                                    if album_files:
                                        post_files.extend([str(f) for f in album_files])
                                        logger.info(
                                            f"アルバムダウンロード完了: {len(album_files)}ファイル"
                                        )
                                else:
                                    logger.warning(f"未対応のメディアタイプ: {media.media_type}")

                            # 投稿情報（キャプションとメタデータ）を保存（UTF-8 BOM付きで保存して文字化けを防ぐ）
                            try:
                                # メタデータファイルのパスを生成
                                metadata_file = download_path / f"{media.pk}_metadata.txt"

                                # 投稿情報を含むメタデータファイルを作成
                                metadata_content = f"投稿ID: {media.pk}\n"

                                if taken_at:
                                    metadata_content += (
                                        f"投稿日時: {taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                    )

                                if hasattr(media, "like_count"):
                                    metadata_content += f"いいね数: {media.like_count}\n"

                                if hasattr(media, "comment_count"):
                                    metadata_content += f"コメント数: {media.comment_count}\n"

                                if hasattr(media, "media_type"):
                                    media_type_names = {1: "画像", 2: "動画", 8: "アルバム"}
                                    metadata_content += f"メディアタイプ: {media.media_type} ({media_type_names.get(media.media_type, '不明')})\n"

                                # キャプションを取得（絵文字も含めてそのまま取得）
                                caption_text = ""
                                if hasattr(media, "caption_text") and media.caption_text:
                                    caption_text = str(
                                        media.caption_text
                                    )  # 文字列に変換して絵文字を保持
                                elif hasattr(media, "caption") and media.caption:
                                    caption_text = str(
                                        media.caption
                                    )  # 文字列に変換して絵文字を保持

                                if caption_text:
                                    metadata_content += f"\n--- キャプション ---\n{caption_text}\n"

                                # UTF-8 BOM付きで保存（Windowsでの文字化けを防ぐ）
                                with open(metadata_file, "w", encoding="utf-8-sig") as f:
                                    f.write(metadata_content)

                                post_files.append(str(metadata_file))
                                logger.info(f"投稿メタデータ保存完了: {metadata_file}")
                            except Exception as metadata_error:
                                logger.warning(f"投稿メタデータ保存エラー: {metadata_error}")

                            if post_files:
                                downloaded_files.extend(post_files)
                                logger.info(
                                    f"投稿 {media.pk} のダウンロード完了: {len(post_files)}ファイル"
                                )

                            break  # 成功したらループを抜ける

                        except ClientError as e:
                            error_str = str(e).lower()
                            # レート制限エラーを検出
                            if "feedback_required" in error_str:
                                rate_limit_detected = True
                            
                            if attempt < retry_attempts - 1:
                                logger.warning(
                                    f"ダウンロードエラー (試行 {attempt + 1}/{retry_attempts}): {e}"
                                )
                                time.sleep(self.delay_between_requests * (attempt + 1))
                            else:
                                logger.error(f"ダウンロード失敗 (最大試行回数に達しました): {e}")
                                raise

                    # リクエスト間の待機
                    if idx < len(medias):
                        time.sleep(self.delay_between_requests)

                except Exception as e:
                    logger.error(f"投稿のダウンロードエラー (media_pk: {media.pk}): {e}")
                    error_str = str(e).lower()
                    # レート制限エラーを検出
                    if "feedback_required" in error_str:
                        rate_limit_detected = True
                    continue

            logger.info(f"投稿のダウンロード完了: {username} ({len(downloaded_files)}ファイル)")
            
            # レート制限エラーが検出された場合、エラー情報を返す
            if rate_limit_detected:
                return {
                    "files": downloaded_files,
                    "error": "feedback_required: Rate limit error detected"
                }

        except Exception as e:
            logger.error(f"投稿ダウンロード処理エラー ({username}): {e}")
            error_str = str(e).lower()
            if "feedback_required" in error_str:
                return {
                    "files": downloaded_files,
                    "error": str(e)
                }

        return downloaded_files

    def download_stories(
        self, username: str, user_id: str, limit: int = 10, retry_attempts: int = 3
    ) -> list[str]:
        """
        ストーリーをダウンロード

        Args:
            username: ユーザー名
            user_id: ユーザーID
            limit: ダウンロードするストーリー数
            retry_attempts: リトライ回数

        Returns:
            ダウンロードしたファイルのパスリスト
        """
        downloaded_files = []

        try:
            logger.info(f"ストーリーのダウンロードを開始: {username} (最大{limit}件)")

            # ストーリーを取得
            try:
                stories = self.client.user_stories(user_id)
            except Exception as e:
                error_str = str(e).lower()
                if "challenge" in error_str or "challenge_required" in error_str:
                    logger.warning(
                        f"Instagramのセキュリティチェックが要求されました: {username}。ブラウザでログインして確認してください。"
                    )
                    return downloaded_files
                raise

            if not stories:
                logger.info(f"ストーリーが見つかりませんでした: {username}")
                return downloaded_files

            # 制限を適用
            stories = stories[:limit]
            logger.info(f"{len(stories)}件のストーリーを取得しました")

            # 各ストーリーをダウンロード
            for idx, story in enumerate(stories, 1):
                try:
                    logger.info(f"[{idx}/{len(stories)}] ストーリーをダウンロード中: {story.pk}")

                    # ストーリーのアップロード日時を取得
                    from datetime import datetime

                    taken_at = None
                    if hasattr(story, "taken_at") and story.taken_at:
                        if isinstance(story.taken_at, (int, float)):
                            taken_at = datetime.fromtimestamp(story.taken_at)
                        else:
                            taken_at = story.taken_at

                    # 各ストーリーのアップロード日時でフォルダを作成
                    download_path = get_download_path(
                        self.base_directory,
                        username,
                        "stories",
                        self.organize_by_company,
                        self.organize_by_date,
                        taken_at,
                    )

                    # 最適化: storyオブジェクトから直接URLを取得する方法を最初に試す（バリデーションエラーを避けるため）
                    file_path = None

                    # 方法1: storyオブジェクトから直接URLを取得してダウンロード（最も確実で高速）
                    try:
                        download_url = None
                        filename = None

                        # storyオブジェクトの属性を確認（優先順位順、より多くの属性をチェック）
                        # まず直接的なURL属性を確認
                        if hasattr(story, "video_url") and story.video_url:
                            download_url = str(story.video_url)
                            filename = f"{story.pk}.mp4"
                            logger.info(f"video_urlから取得: {download_url[:50]}...")
                        elif hasattr(story, "thumbnail_url") and story.thumbnail_url:
                            download_url = str(story.thumbnail_url)
                            # 拡張子を判定
                            if download_url.endswith(".mp4") or download_url.endswith(".webm"):
                                filename = f"{story.pk}.mp4"
                            else:
                                filename = f"{story.pk}.jpg"
                            logger.info(f"thumbnail_urlから取得: {download_url[:50]}...")

                        # media_typeに基づいてURLを取得（動画の場合は優先的にvideo_versionsから取得）
                        if not download_url and hasattr(story, "media_type"):
                            logger.info(f"media_type: {story.media_type}")
                            if story.media_type == 2:  # Video
                                # video_versionsから取得（動画の場合は最優先）
                                if hasattr(story, "video_versions") and story.video_versions:
                                    try:
                                        if len(story.video_versions) > 0:
                                            video_version = story.video_versions[0]
                                            if hasattr(video_version, "url"):
                                                download_url = str(video_version.url)
                                                filename = f"{story.pk}.mp4"
                                                logger.info(
                                                    f"video_versions[0].urlから取得（動画）: {download_url[:50]}..."
                                                )
                                    except (AttributeError, IndexError, TypeError) as e:
                                        logger.debug(f"video_versionsからの取得エラー: {e}")
                                # video_urlを再確認
                                if (
                                    not download_url
                                    and hasattr(story, "video_url")
                                    and story.video_url
                                ):
                                    download_url = str(story.video_url)
                                    filename = f"{story.pk}.mp4"
                                    logger.info(
                                        f"video_urlから再取得（動画）: {download_url[:50]}..."
                                    )
                            else:  # Photo (media_type == 1)
                                # image_versions2から取得
                                if hasattr(story, "image_versions2") and story.image_versions2:
                                    try:
                                        if (
                                            hasattr(story.image_versions2, "candidates")
                                            and story.image_versions2.candidates
                                        ):
                                            if len(story.image_versions2.candidates) > 0:
                                                candidate = story.image_versions2.candidates[0]
                                                if hasattr(candidate, "url"):
                                                    download_url = str(candidate.url)
                                                    filename = f"{story.pk}.jpg"
                                                    logger.debug(
                                                        f"image_versions2.candidates[0].urlから取得: {download_url}"
                                                    )
                                    except (AttributeError, IndexError, TypeError) as e:
                                        logger.debug(f"image_versions2からの取得エラー: {e}")
                                # thumbnail_urlを再確認
                                if (
                                    not download_url
                                    and hasattr(story, "thumbnail_url")
                                    and story.thumbnail_url
                                ):
                                    download_url = str(story.thumbnail_url)
                                    filename = f"{story.pk}.jpg"
                                    logger.debug(f"thumbnail_urlから再取得: {download_url}")

                        # 辞書形式でも確認（念のため）
                        if not download_url:
                            try:
                                story_dict = story.dict() if hasattr(story, "dict") else None
                                if story_dict:
                                    if story_dict.get("video_url"):
                                        download_url = str(story_dict["video_url"])
                                        filename = f"{story.pk}.mp4"
                                    elif story_dict.get("thumbnail_url"):
                                        download_url = str(story_dict["thumbnail_url"])
                                        filename = f"{story.pk}.jpg"
                            except Exception:
                                pass

                        if download_url:
                            # requestsライブラリを使って直接ダウンロード（より確実）
                            try:
                                import requests

                                # instagrapiのClientからセッション情報を取得
                                # Clientオブジェクトにはprivate属性があるので、それを使ってリクエスト
                                headers = {
                                    "User-Agent": self.client.private.headers.get(
                                        "User-Agent", "Mozilla/5.0"
                                    ),
                                }

                                response = requests.get(download_url, headers=headers, timeout=30)
                                response.raise_for_status()

                                # ファイルパスを生成
                                file_path = download_path / filename

                                # ファイルを保存
                                with open(file_path, "wb") as f:
                                    f.write(response.content)

                                # ストーリーの投稿日時を取得してメタデータファイルを作成
                                try:
                                    from datetime import datetime

                                    story_metadata_file = download_path / f"{story.pk}_metadata.txt"
                                    metadata_content = f"ストーリーID: {story.pk}\n"

                                    if hasattr(story, "taken_at") and story.taken_at:
                                        if isinstance(story.taken_at, (int, float)):
                                            taken_at = datetime.fromtimestamp(story.taken_at)
                                        else:
                                            taken_at = story.taken_at
                                        metadata_content += (
                                            f"投稿日時: {taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                        )

                                    if (
                                        hasattr(story, "imported_taken_at")
                                        and story.imported_taken_at
                                    ):
                                        if isinstance(story.imported_taken_at, (int, float)):
                                            imported_taken_at = datetime.fromtimestamp(
                                                story.imported_taken_at
                                            )
                                        else:
                                            imported_taken_at = story.imported_taken_at
                                        metadata_content += f"インポート日時: {imported_taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

                                    if hasattr(story, "media_type"):
                                        metadata_content += f"メディアタイプ: {story.media_type} ({'動画' if story.media_type == 2 else '画像'})\n"

                                    # UTF-8 BOM付きで保存（Windowsでの文字化けを防ぐ）
                                    with open(story_metadata_file, "w", encoding="utf-8-sig") as f:
                                        f.write(metadata_content)

                                    downloaded_files.append(str(story_metadata_file))
                                    logger.debug(
                                        f"ストーリーメタデータ保存完了: {story_metadata_file}"
                                    )
                                except Exception as metadata_error:
                                    logger.debug(
                                        f"ストーリーメタデータ保存エラー: {metadata_error}"
                                    )

                                downloaded_files.append(str(file_path))
                                logger.info(
                                    f"storyオブジェクトからURL直接ダウンロード完了: {file_path}"
                                )
                            except Exception as download_error:
                                logger.warning(
                                    f"requests.get()でのダウンロード失敗、story_download_by_urlを試行: {download_error}"
                                )
                                # フォールバック: story_download_by_urlを試す
                                try:
                                    file_path = self.client.story_download_by_url(
                                        download_url, filename=filename, folder=str(download_path)
                                    )
                                    if file_path:
                                        # ストーリーの投稿日時を取得してメタデータファイルを作成（UTF-8 BOM付きで保存）
                                        try:
                                            story_metadata_file = (
                                                download_path / f"{story.pk}_metadata.txt"
                                            )
                                            metadata_content = f"ストーリーID: {story.pk}\n"

                                            if taken_at:
                                                metadata_content += f"投稿日時: {taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

                                            if (
                                                hasattr(story, "imported_taken_at")
                                                and story.imported_taken_at
                                            ):
                                                if isinstance(
                                                    story.imported_taken_at, (int, float)
                                                ):
                                                    imported_taken_at = datetime.fromtimestamp(
                                                        story.imported_taken_at
                                                    )
                                                else:
                                                    imported_taken_at = story.imported_taken_at
                                                metadata_content += f"インポート日時: {imported_taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

                                            if hasattr(story, "media_type"):
                                                metadata_content += f"メディアタイプ: {story.media_type} ({'動画' if story.media_type == 2 else '画像'})\n"

                                            # UTF-8 BOM付きで保存（Windowsでの文字化けを防ぐ）
                                            with open(
                                                story_metadata_file, "w", encoding="utf-8-sig"
                                            ) as f:
                                                f.write(metadata_content)

                                            downloaded_files.append(str(story_metadata_file))
                                            logger.debug(
                                                f"ストーリーメタデータ保存完了: {story_metadata_file}"
                                            )
                                        except Exception as metadata_error:
                                            logger.debug(
                                                f"ストーリーメタデータ保存エラー: {metadata_error}"
                                            )

                                        downloaded_files.append(str(file_path))
                                        logger.info(
                                            f"story_download_by_urlでダウンロード完了: {file_path}"
                                        )
                                except Exception as fallback_error:
                                    logger.warning(f"story_download_by_urlも失敗: {fallback_error}")
                                    raise download_error
                        else:
                            logger.warning(
                                f"storyオブジェクトからURLを取得できませんでした (story_pk: {story.pk})"
                            )
                            # デバッグ: storyオブジェクトの属性を確認
                            try:
                                story_dict = story.dict() if hasattr(story, "dict") else {}
                                available_keys = [
                                    k
                                    for k in story_dict.keys()
                                    if "url" in k.lower()
                                    or "media" in k.lower()
                                    or "image" in k.lower()
                                    or "video" in k.lower()
                                ]
                                logger.debug(f"storyオブジェクトのURL関連キー: {available_keys}")
                            except Exception:
                                pass

                    except Exception as url_error:
                        logger.warning(f"storyオブジェクトからのURL取得失敗: {url_error}")

                    # 方法2: 通常のstory_downloadを試す（方法1が失敗した場合のみ、リトライなし）
                    if not file_path:
                        try:
                            file_path = self.client.story_download(
                                story.pk, folder=str(download_path)
                            )

                            if file_path:
                                # ストーリーの投稿日時を取得してメタデータファイルを作成
                                try:
                                    from datetime import datetime

                                    story_metadata_file = download_path / f"{story.pk}_metadata.txt"
                                    metadata_content = f"ストーリーID: {story.pk}\n"

                                    if hasattr(story, "taken_at") and story.taken_at:
                                        if isinstance(story.taken_at, (int, float)):
                                            taken_at = datetime.fromtimestamp(story.taken_at)
                                        else:
                                            taken_at = story.taken_at
                                        metadata_content += (
                                            f"投稿日時: {taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                        )

                                    if (
                                        hasattr(story, "imported_taken_at")
                                        and story.imported_taken_at
                                    ):
                                        if isinstance(story.imported_taken_at, (int, float)):
                                            imported_taken_at = datetime.fromtimestamp(
                                                story.imported_taken_at
                                            )
                                        else:
                                            imported_taken_at = story.imported_taken_at
                                        metadata_content += f"インポート日時: {imported_taken_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

                                    if hasattr(story, "media_type"):
                                        metadata_content += f"メディアタイプ: {story.media_type} ({'動画' if story.media_type == 2 else '画像'})\n"

                                    # UTF-8 BOM付きで保存（Windowsでの文字化けを防ぐ）
                                    with open(story_metadata_file, "w", encoding="utf-8-sig") as f:
                                        f.write(metadata_content)

                                    downloaded_files.append(str(story_metadata_file))
                                    logger.debug(
                                        f"ストーリーメタデータ保存完了: {story_metadata_file}"
                                    )
                                except Exception as metadata_error:
                                    logger.debug(
                                        f"ストーリーメタデータ保存エラー: {metadata_error}"
                                    )

                                downloaded_files.append(str(file_path))
                                logger.info(f"通常方法でダウンロード完了: {file_path}")

                        except (ValueError, Exception) as validation_error:
                            # Pydanticバリデーションエラーなどの場合
                            error_str = str(validation_error).lower()
                            if (
                                "validation" in error_str
                                or "scans_profile" in error_str
                                or "pydantic" in error_str
                            ):
                                logger.debug(
                                    f"バリデーションエラー（予想通り）: {validation_error}"
                                )
                                # storyオブジェクトから再度URL取得を試みる（リトライ）
                                try:
                                    # より積極的にURLを探す
                                    for attr_name in [
                                        "video_url",
                                        "thumbnail_url",
                                        "image_url",
                                        "media_url",
                                    ]:
                                        if hasattr(story, attr_name):
                                            attr_value = getattr(story, attr_name)
                                            if attr_value:
                                                download_url = str(attr_value)
                                                filename = f"{story.pk}.{'mp4' if 'video' in attr_name.lower() else 'jpg'}"
                                                try:
                                                    file_path = self.client.story_download_by_url(
                                                        download_url,
                                                        filename=filename,
                                                        folder=str(download_path),
                                                    )
                                                    if file_path:
                                                        downloaded_files.append(str(file_path))
                                                        logger.info(
                                                            f"代替属性({attr_name})からダウンロード完了: {file_path}"
                                                        )
                                                        break
                                                except Exception:
                                                    continue
                                    if not file_path:
                                        logger.warning(
                                            f"ストーリー {story.pk} のダウンロードをスキップします（URL取得不可）"
                                        )
                                except Exception as retry_error:
                                    logger.debug(f"代替属性からのURL取得も失敗: {retry_error}")
                            else:
                                # その他のエラーはログに記録して続行
                                logger.warning(f"ストーリーダウンロードエラー: {validation_error}")

                    # ダウンロードに失敗した場合は次のストーリーに進む
                    if not file_path:
                        logger.warning(
                            f"ストーリー {story.pk} のダウンロードに失敗しました（すべての方法を試しました）"
                        )

                    # リクエスト間の待機
                    if idx < len(stories):
                        time.sleep(self.delay_between_requests)

                except Exception as e:
                    logger.error(f"ストーリーのダウンロードエラー (story_pk: {story.pk}): {e}")
                    continue

            logger.info(
                f"ストーリーのダウンロード完了: {username} ({len(downloaded_files)}ファイル)"
            )

        except Exception as e:
            logger.error(f"ストーリーダウンロード処理エラー ({username}): {e}")

        return downloaded_files

    def download_all(
        self,
        username: str,
        user_id: str,
        download_posts: bool = True,
        download_stories: bool = True,
        posts_limit: int = 20,
        stories_limit: int = 10,
    ) -> dict[str, list[str]]:
        """
        投稿とストーリーの両方をダウンロード

        Args:
            username: ユーザー名
            user_id: ユーザーID
            download_posts: 投稿をダウンロードするか
            download_stories: ストーリーをダウンロードするか
            posts_limit: ダウンロードする投稿数
            stories_limit: ダウンロードするストーリー数

        Returns:
            ダウンロード結果の辞書
        """
        results = {"posts": [], "stories": []}

        if download_posts:
            posts_result = self.download_posts(username, user_id, posts_limit)
            # レート制限エラーが含まれている場合
            if isinstance(posts_result, dict) and "error" in posts_result:
                results["posts"] = posts_result.get("files", [])
                results["error"] = posts_result["error"]
            else:
                results["posts"] = posts_result
            time.sleep(self.delay_between_requests)

        if download_stories:
            results["stories"] = self.download_stories(username, user_id, stories_limit)

        return results
