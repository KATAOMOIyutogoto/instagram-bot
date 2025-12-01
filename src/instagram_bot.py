"""
Instagramボットのコアクラス
"""

import logging
import time
from pathlib import Path
from typing import Any

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, LoginRequired, TwoFactorRequired

logger = logging.getLogger(__name__)


class InstagramBot:
    """Instagramボットのメインクラス"""

    def __init__(self, username: str, password: str, session_file: str = "data/session.json"):
        """
        Args:
            username: Instagramのユーザー名
            password: Instagramのパスワード
            session_file: セッションファイルのパス
        """
        self.username = username
        self.password = password
        self.session_file = session_file
        self.client = Client()
        self.is_logged_in = False

    def login(self, verification_code: str | None = None) -> bool:
        """
        Instagramにログイン

        Args:
            verification_code: 2FA認証コード（必要な場合）

        Returns:
            ログイン成功したかどうか
        """
        try:
            # セッションファイルが存在する場合は読み込む
            session_exists = Path(self.session_file).exists()
            if session_exists:
                logger.info(f"セッションファイルを読み込みます: {self.session_file}")
                self.client.load_settings(self.session_file)
                # セッションファイルを読み込んだ場合、接続確認を行う
                try:
                    self.client.account_info()
                    logger.info("セッションファイルが有効です。ログイン不要")
                    self.is_logged_in = True
                    return True
                except ChallengeRequired:
                    logger.warning(
                        f"セッションファイル読み込み時にチャレンジ認証が必要です（アカウント: {self.username}）。"
                        "セッションファイルを削除します。次回実行時（1時間後）にユーザー名とパスワードで再ログインを試みます。"
                    )
                    # セッションファイルを削除（次回実行時にユーザー名とパスワードで再ログインを試みるため）
                    Path(self.session_file).unlink()
                    logger.info("チャレンジ認証が必要なため、セッションファイルを削除しました")
                    # 新しいクライアントインスタンスを作成
                    self.client = Client()
                except (LoginRequired, Exception) as e:
                    logger.warning(f"セッションファイルが無効です: {e}。再ログインを試みます")
                    # 無効なセッションファイルを削除
                    Path(self.session_file).unlink()
                    logger.info("無効なセッションファイルを削除しました")
                    # 新しいクライアントインスタンスを作成
                    self.client = Client()

            # ログイン試行
            try:
                self.client.login(self.username, self.password, verification_code=verification_code)
                logger.info("ログインに成功しました")
                
                # ログインが実際に成功したか確認
                try:
                    self.client.account_info()
                    logger.info("接続確認に成功しました")
                except LoginRequired:
                    logger.warning("接続確認でログインが必要です。ログインが無効の可能性があります")
                    self.is_logged_in = False
                    return False
                except Exception as e:
                    logger.warning(f"接続確認エラー: {e}。ログインが無効の可能性があります")
                    self.is_logged_in = False
                    return False
                
                self.is_logged_in = True

                # セッションを保存
                self.client.dump_settings(self.session_file)
                logger.info(f"セッションを保存しました: {self.session_file}")
                return True

            except TwoFactorRequired:
                logger.warning("2FA認証が必要です。verification_codeを指定してください")
                return False

            except ChallengeRequired:
                logger.warning(
                    f"チャレンジ認証が必要です（アカウント: {self.username}）。"
                    "セッションファイルを削除します。次回実行時（1時間後）にユーザー名とパスワードで再ログインを試みます。"
                )
                # セッションファイルを削除（次回実行時にユーザー名とパスワードで再ログインを試みるため）
                if Path(self.session_file).exists():
                    Path(self.session_file).unlink()
                    logger.info("チャレンジ認証が必要なため、セッションファイルを削除しました")
                return False

            except LoginRequired:
                logger.warning("ログインが必要です。セッションが無効の可能性があります")
                # セッションファイルを削除
                if Path(self.session_file).exists():
                    Path(self.session_file).unlink()
                    logger.info("無効なセッションファイルを削除しました")
                # 新しいクライアントインスタンスを作成して再ログインを試みる
                self.client = Client()
                try:
                    self.client.login(self.username, self.password, verification_code=verification_code)
                    logger.info("再ログインに成功しました")
                    
                    # ログインが実際に成功したか確認
                    try:
                        self.client.account_info()
                        logger.info("再ログイン後の接続確認に成功しました")
                    except LoginRequired:
                        logger.error("再ログイン後の接続確認でログインが必要です。認証情報を確認してください")
                        self.is_logged_in = False
                        return False
                    except Exception as e:
                        logger.warning(f"再ログイン後の接続確認エラー: {e}")
                        self.is_logged_in = False
                        return False
                    
                    self.is_logged_in = True
                    # セッションを保存
                    self.client.dump_settings(self.session_file)
                    logger.info(f"セッションを保存しました: {self.session_file}")
                    return True
                except Exception as e:
                    logger.error(f"再ログインエラー: {e}")
                    return False

        except Exception as e:
            logger.error(f"ログインエラー: {e}")
            return False

    def get_user_id(self, identifier: str, max_retries: int = 3, delay: float = 2.0) -> str | None:
        """
        ユーザー名またはユーザーIDからユーザーIDを取得

        Args:
            identifier: Instagramのユーザー名（例: "username"）またはユーザーID（例: "123456789"）
            max_retries: 429エラー時の最大リトライ回数
            delay: API呼び出し前の待機時間（秒）

        Returns:
            ユーザーID、取得失敗時はNone
        """
        try:
            # 数値のみの場合は既にユーザーIDと判断
            if identifier.isdigit():
                logger.info(f"ユーザーIDとして認識: {identifier}")
                return identifier

            # API呼び出し前に待機時間を設ける（レート制限対策）
            if delay > 0:
                time.sleep(delay)

            # ユーザー名からユーザーIDを取得
            user_id = self.client.user_id_from_username(identifier)
            logger.info(f"ユーザーIDを取得しました: {identifier} -> {user_id}")
            return user_id
        except LoginRequired:
            logger.warning(f"ログインが必要です。再ログインを試みます: {identifier}")
            # 再ログインを試みる
            if self.login():
                try:
                    # 再ログイン後、再度ユーザーIDを取得
                    user_id = self.client.user_id_from_username(identifier)
                    logger.info(f"再ログイン後、ユーザーIDを取得しました: {identifier} -> {user_id}")
                    return user_id
                except Exception as e:
                    logger.error(f"再ログイン後のユーザーID取得エラー ({identifier}): {e}")
                    return None
            else:
                logger.error(f"再ログインに失敗しました: {identifier}")
                return None
        except Exception as e:
            error_str = str(e).lower()
            # 429エラー（レート制限）を検出
            if "429" in error_str or "too many" in error_str or "rate limit" in error_str:
                logger.warning(f"レート制限エラー ({identifier}): {e}")
                # リトライ処理
                for retry in range(max_retries):
                    wait_time = 60 * (retry + 1)  # 60秒、120秒、180秒と増やす
                    logger.info(f"レート制限のため {wait_time}秒待機してからリトライします ({retry + 1}/{max_retries})")
                    time.sleep(wait_time)
                    try:
                        user_id = self.client.user_id_from_username(identifier)
                        logger.info(f"リトライ後、ユーザーIDを取得しました: {identifier} -> {user_id}")
                        return user_id
                    except Exception as retry_error:
                        if retry < max_retries - 1:
                            logger.warning(f"リトライ {retry + 1}/{max_retries} 失敗: {retry_error}")
                        else:
                            logger.error(f"レート制限エラー: 最大リトライ回数に達しました ({identifier})")
                            return None
                return None
            else:
                logger.error(f"ユーザーID取得エラー ({identifier}): {e}")
                return None

    def get_user_info(self, username: str) -> dict[str, Any] | None:
        """
        ユーザー情報を取得

        Args:
            username: Instagramのユーザー名

        Returns:
            ユーザー情報の辞書、取得失敗時はNone
        """
        try:
            user_info = self.client.user_info_by_username(username)
            return {
                "pk": user_info.pk,
                "username": user_info.username,
                "full_name": user_info.full_name,
                "biography": user_info.biography,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "media_count": user_info.media_count,
                "is_private": user_info.is_private,
                "is_verified": user_info.is_verified,
            }
        except LoginRequired:
            logger.warning(f"ログインが必要です。再ログインを試みます: {username}")
            # 再ログインを試みる
            if self.login():
                try:
                    # 再ログイン後、再度ユーザー情報を取得
                    user_info = self.client.user_info_by_username(username)
                    return {
                        "pk": user_info.pk,
                        "username": user_info.username,
                        "full_name": user_info.full_name,
                        "biography": user_info.biography,
                        "follower_count": user_info.follower_count,
                        "following_count": user_info.following_count,
                        "media_count": user_info.media_count,
                        "is_private": user_info.is_private,
                        "is_verified": user_info.is_verified,
                    }
                except Exception as e:
                    logger.error(f"再ログイン後のユーザー情報取得エラー ({username}): {e}")
                    return None
            else:
                logger.error(f"再ログインに失敗しました: {username}")
                return None
        except Exception as e:
            logger.error(f"ユーザー情報取得エラー ({username}): {e}")
            return None

    def check_connection(self) -> bool:
        """接続状態を確認"""
        if not self.is_logged_in:
            return False

        try:
            # 自分のアカウント情報を取得して接続確認
            self.client.account_info()
            return True
        except Exception as e:
            logger.warning(f"接続確認エラー: {e}")
            self.is_logged_in = False
            return False

    def wait_between_requests(self, delay: float = 2.0) -> None:
        """リクエスト間の待機時間"""
        time.sleep(delay)

    def __enter__(self):
        """コンテキストマネージャーとして使用する場合"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了時"""
        # 必要に応じてクリーンアップ処理
        pass
