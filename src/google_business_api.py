"""
Google Business Profile API クライアント
Google Business Profile Management APIを使用して投稿をアップロード
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning(
        "requestsライブラリがインストールされていません。pip install requests を実行してください。"
    )

try:
    import io

    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logging.warning(
        "Google API クライアントライブラリがインストールされていません。pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib を実行してください。"
    )

logger = logging.getLogger(__name__)


class GoogleBusinessProfileAPI:
    """Google Business Profile API クライアント"""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
        scopes: list[str] | None = None,
    ):
        """
        Args:
            credentials_path: サービスアカウントの認証情報ファイルのパス（JSON）
            token_path: OAuth2トークンファイルのパス（JSON）
            scopes: APIスコープのリスト
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API クライアントライブラリがインストールされていません。\n"
                "以下のコマンドでインストールしてください：\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        self.credentials_path = credentials_path
        self.token_path = token_path

        # Google Business Profile API のスコープ
        if scopes is None:
            self.scopes = ["https://www.googleapis.com/auth/business.manage"]
        else:
            self.scopes = scopes

        self.service = None
        self.credentials = None
        self._authenticate()

    def _authenticate(self):
        """認証を実行"""
        try:
            import json

            # まず、既存のトークンファイルがあるか確認
            if self.token_path and Path(self.token_path).exists():
                try:
                    logger.info(f"既存のOAuth2トークンを確認: {self.token_path}")
                    from google.oauth2.credentials import Credentials

                    self.credentials = Credentials.from_authorized_user_file(
                        self.token_path, scopes=self.scopes
                    )

                    # トークンの有効性をチェック
                    if not self.credentials.valid:
                        if self.credentials.expired:
                            if self.credentials.refresh_token:
                                logger.info("トークンが期限切れです。リフレッシュ中...")
                                try:
                                    self.credentials.refresh(Request())
                                    # リフレッシュしたトークンを保存
                                    with open(self.token_path, "w") as token:
                                        token.write(self.credentials.to_json())
                                    logger.info("トークンをリフレッシュしました")
                                except Exception as refresh_error:
                                    logger.warning(
                                        f"トークンのリフレッシュに失敗しました: {refresh_error}"
                                    )
                                    logger.info("新しいトークンを取得します...")
                                    # トークンファイルを削除して再認証
                                    Path(self.token_path).unlink()
                                    self.credentials = None
                            else:
                                logger.warning(
                                    "リフレッシュトークンがありません。新しいトークンを取得します..."
                                )
                                # トークンファイルを削除して再認証
                                Path(self.token_path).unlink()
                                self.credentials = None
                        else:
                            logger.warning("トークンが無効です。新しいトークンを取得します...")
                            # トークンファイルを削除して再認証
                            Path(self.token_path).unlink()
                            self.credentials = None

                    # トークンが有効な場合、APIサービスを構築
                    if self.credentials and self.credentials.valid:
                        self.service = build("mybusiness", "v4", credentials=self.credentials)
                        logger.info(
                            "Google Business Profile API への認証が完了しました（既存トークンを使用）"
                        )
                        return
                    else:
                        logger.info("新しいトークンを取得します...")

                except json.JSONDecodeError as e:
                    logger.warning(f"トークンファイルの形式が不正です: {e}")
                    logger.info("トークンファイルを削除して再認証します...")
                    try:
                        Path(self.token_path).unlink()
                    except:
                        pass
                    self.credentials = None
                except Exception as e:
                    logger.warning(f"既存のトークンで認証できませんでした: {e}")
                    logger.info("新しいトークンを取得します...")
                    # トークンファイルを削除して再認証
                    try:
                        Path(self.token_path).unlink()
                    except:
                        pass
                    self.credentials = None

            # credentials.json が存在する場合、形式を判定
            if self.credentials_path and Path(self.credentials_path).exists():
                with open(self.credentials_path, encoding="utf-8") as f:
                    creds_data = json.load(f)

                # サービスアカウント形式かどうかを判定
                if creds_data.get("type") == "service_account" and "client_email" in creds_data:
                    # サービスアカウント認証
                    logger.info(f"サービスアカウント認証を使用: {self.credentials_path}")
                    self.credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_path, scopes=self.scopes
                    )
                elif "web" in creds_data or "installed" in creds_data:
                    # OAuth 2.0クライアントID形式
                    logger.info(
                        f"OAuth 2.0クライアントID形式の認証情報を検出: {self.credentials_path}"
                    )

                    # クライアントID情報を取得
                    client_config = creds_data.get("web") or creds_data.get("installed")
                    if not client_config:
                        raise ValueError("OAuth 2.0クライアントID情報が見つかりません")

                    # プロジェクトIDを保存（後でエラーメッセージで使用）
                    project_id = client_config.get("project_id", "不明")

                    # redirect_uris の順序を調整: 'urn:ietf:wg:oauth:2.0:oob' を最初に配置
                    # これは InstalledAppFlow を作成する前に行う必要があります
                    redirect_uris = client_config.get("redirect_uris", [])
                    redirect_uri_to_use = None

                    # 'urn:ietf:wg:oauth:2.0:oob' を優先的に使用
                    if "urn:ietf:wg:oauth:2.0:oob" in redirect_uris:
                        redirect_uri_to_use = "urn:ietf:wg:oauth:2.0:oob"
                        # 順序を調整（メモリ上のみ、ファイルには保存しない）
                        redirect_uris.remove("urn:ietf:wg:oauth:2.0:oob")
                        redirect_uris.insert(0, "urn:ietf:wg:oauth:2.0:oob")
                        client_config["redirect_uris"] = redirect_uris
                        logger.info(
                            "リダイレクトURIの順序を調整: urn:ietf:wg:oauth:2.0:oob を最初に配置"
                        )
                    elif redirect_uris:
                        redirect_uri_to_use = redirect_uris[0]
                        logger.info(f"使用するリダイレクトURI: {redirect_uri_to_use}")
                    else:
                        # redirect_uris が空の場合は追加
                        redirect_uri_to_use = "urn:ietf:wg:oauth:2.0:oob"
                        redirect_uris = [redirect_uri_to_use]
                        client_config["redirect_uris"] = redirect_uris
                        logger.info("リダイレクトURIを追加: urn:ietf:wg:oauth:2.0:oob")

                    # フローを作成（redirect_uris の順序が調整された creds_data を使用）
                    flow = InstalledAppFlow.from_client_config(creds_data, self.scopes)

                    # oauth2session の redirect_uri を明示的に設定
                    # これにより、authorization_url と fetch_token で同じ redirect_uri が使用される
                    if hasattr(flow, "oauth2session") and flow.oauth2session:
                        flow.oauth2session.redirect_uri = redirect_uri_to_use
                        logger.info(f"oauth2session の redirect_uri を設定: {redirect_uri_to_use}")

                    # コンソールベース認証を使用
                    logger.info("=" * 60)
                    logger.info("OAuth 2.0 認証を開始します")
                    logger.info("=" * 60)
                    logger.info(f"使用するリダイレクトURI: {redirect_uri_to_use}")

                    # 認証URLを生成
                    # InstalledAppFlow は redirect_uris の最初のURIを自動的に使用します
                    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

                    # 生成されたURLに redirect_uri が含まれているか確認
                    # URLエンコードされている可能性があるため、両方をチェック
                    if "redirect_uri=" not in auth_url and "redirect_uri%3D" not in auth_url:
                        logger.warning("認証URLに redirect_uri パラメータが含まれていません")
                        logger.info("手動で redirect_uri を追加します...")
                        # URLに redirect_uri を追加
                        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

                        parsed = urlparse(auth_url)
                        params = parse_qs(parsed.query)
                        params["redirect_uri"] = [redirect_uri_to_use]
                        new_query = urlencode(params, doseq=True)
                        auth_url = urlunparse(parsed._replace(query=new_query))
                        logger.info("修正後の認証URLに redirect_uri を追加しました")
                    else:
                        logger.info("認証URLに redirect_uri が含まれています")

                    print("\n" + "=" * 60)
                    print("以下の手順で認証を行ってください：")
                    print("=" * 60)
                    print("\n1. 以下のURLをブラウザで開いてください：")
                    print(f"\n   {auth_url}\n")
                    print("2. Googleアカウントでログインし、アクセスを許可してください")
                    print("3. 認証が完了すると、認証コードが表示されます")
                    print("4. その認証コードをコピーして、以下に入力してください\n")
                    print("=" * 60 + "\n")

                    # 認証コードを入力（最大3回まで再試行可能）
                    max_attempts = 3
                    code = None

                    for attempt in range(max_attempts):
                        try:
                            # EOFエラーをキャッチして、より明確なメッセージを表示
                            try:
                                code = input("認証コードを入力してください: ").strip()
                            except (EOFError, KeyboardInterrupt):
                                # 自動実行時やパイプ経由の実行時に発生
                                logger.error(
                                    "認証コードの入力ができませんでした（対話的入力が必要です）"
                                )
                                raise ValueError(
                                    "認証コードの入力に失敗しました。\n"
                                    "対話的な実行環境で実行してください。\n"
                                    "または、ブラウザで認証URLを開いて認証コードを取得し、"
                                    "手動で config/token.json を作成してください。"
                                )

                            if not code:
                                if attempt < max_attempts - 1:
                                    print(
                                        "認証コードが入力されませんでした。もう一度入力してください。"
                                    )
                                    continue
                                else:
                                    raise ValueError("認証コードが入力されませんでした")

                            # トークンを取得
                            logger.info("認証コードを交換中...")
                            logger.info(f"使用するリダイレクトURI: {redirect_uri_to_use}")
                            logger.info(f"認証コードの長さ: {len(code)}")
                            logger.info(f"認証コードの先頭10文字: {code[:10]}...")

                            # oauth2session の redirect_uri が正しく設定されているか確認
                            if hasattr(flow, "oauth2session") and flow.oauth2session:
                                if flow.oauth2session.redirect_uri != redirect_uri_to_use:
                                    logger.warning(
                                        "oauth2session の redirect_uri が不一致です。再設定します。"
                                    )
                                    logger.warning(f"  現在: {flow.oauth2session.redirect_uri}")
                                    logger.warning(f"  設定: {redirect_uri_to_use}")
                                    flow.oauth2session.redirect_uri = redirect_uri_to_use

                            # fetch_token を呼び出す（oauth2session の redirect_uri が使用される）
                            # パラメータを渡さないことで、oauth2session に設定された redirect_uri が使用される
                            flow.fetch_token(code=code)

                            self.credentials = flow.credentials
                            logger.info("認証が完了しました")
                            break  # 成功したらループを抜ける

                        except ValueError as e:
                            # ValueError はそのまま再スロー（EOFエラーの場合）
                            if "認証コードの入力に失敗しました" in str(e):
                                raise
                            error_msg = str(e)
                            logger.error(f"認証コードの処理に失敗しました: {error_msg}")
                            print(f"\n❌ エラー: {error_msg}")
                            print("確認事項:")
                            print(
                                "1. 認証コードを正しくコピー＆ペーストしてください（前後の空白を削除）"
                            )
                            print(
                                "2. 認証コードの有効期限（通常10分）が切れていないか確認してください"
                            )
                            print(
                                "3. 認証URLに redirect_uri パラメータが含まれているか確認してください"
                            )
                            if attempt < max_attempts - 1:
                                print(
                                    f"\nもう一度入力してください（残り{max_attempts - attempt - 1}回）\n"
                                )
                                code = None  # リセット
                            else:
                                raise ValueError(
                                    f"認証コードの処理に失敗しました（{max_attempts}回試行）: {e}"
                                )
                        except Exception as e:
                            error_msg = str(e)
                            error_type = type(e).__name__
                            logger.error(
                                f"認証コードの交換に失敗しました ({error_type}): {error_msg}"
                            )
                            print(f"\n❌ エラー ({error_type}): {error_msg}")
                            print("確認事項:")
                            print(
                                "1. 認証コードを正しくコピー＆ペーストしてください（前後の空白を削除）"
                            )
                            print(
                                "2. 認証コードの有効期限（通常10分）が切れていないか確認してください"
                            )
                            print(
                                "3. 認証URLに redirect_uri パラメータが含まれているか確認してください"
                            )
                            if attempt < max_attempts - 1:
                                print(
                                    f"\nもう一度入力してください（残り{max_attempts - attempt - 1}回）\n"
                                )
                                code = None  # リセット
                            else:
                                raise ValueError(
                                    f"認証コードの交換に失敗しました（{max_attempts}回試行）: {e}"
                                )

                    if not code:
                        raise ValueError("認証コードが取得できませんでした")

                    # トークンを保存
                    if self.token_path:
                        token_path_obj = Path(self.token_path)
                        token_path_obj.parent.mkdir(parents=True, exist_ok=True)
                        with open(self.token_path, "w") as token:
                            token.write(self.credentials.to_json())
                        logger.info(f"トークンを保存しました: {self.token_path}")
                    else:
                        logger.warning(
                            "token_pathが指定されていないため、トークンを保存できませんでした"
                        )
                else:
                    raise ValueError(
                        f"認証情報ファイルの形式が不明です: {self.credentials_path}\n"
                        "サービスアカウント形式（type: 'service_account'）または"
                        "OAuth 2.0クライアントID形式（'web' または 'installed' キー）が必要です。"
                    )
            else:
                raise ValueError(
                    "認証情報ファイルが見つかりません。\n" "credentials_path を指定してください。"
                )

            # API サービスを構築
            # Google Business Profile Management API (旧称: Google My Business API)
            try:
                logger.info("Google Business Profile API サービスを構築中...")
                self.service = build("mybusiness", "v4", credentials=self.credentials)
                logger.info("Google Business Profile API への認証が完了しました")
            except Exception as build_error:
                error_msg = str(build_error)
                error_type = type(build_error).__name__
                logger.error(
                    f"Google Business Profile API サービスの構築に失敗しました ({error_type}): {error_msg}"
                )

                # より詳細なエラーメッセージを提供
                if "name" in error_msg.lower() and "version" in error_msg.lower():
                    # プロジェクトIDを取得（可能な場合）
                    project_id = "不明"
                    try:
                        if self.credentials_path and Path(self.credentials_path).exists():
                            import json

                            with open(self.credentials_path, encoding="utf-8") as f:
                                creds = json.load(f)
                                project_id = (
                                    creds.get("installed", {}) or creds.get("web", {})
                                ).get("project_id", "不明")
                    except:
                        pass

                    raise ValueError(
                        f"Google Business Profile API サービスの構築に失敗しました。\n"
                        f"エラー: {error_msg}\n\n"
                        f"確認事項:\n"
                        f"1. Google Cloud Console で「Google Business Profile API」が有効になっているか確認してください\n"
                        f"2. プロジェクトID ({project_id}) が正しいか確認してください\n"
                        f"3. 認証に使用しているGoogleアカウントに適切な権限があるか確認してください\n"
                        f"4. APIが正しく有効化されているか、Google Cloud Console で確認してください"
                    )
                else:
                    raise ValueError(
                        f"Google Business Profile API サービスの構築に失敗しました ({error_type}): {error_msg}\n"
                        f"Google Cloud Console で「Google Business Profile API」が有効になっているか確認してください。"
                    )

        except Exception as e:
            logger.error(f"Google Business Profile API の認証エラー: {e}")
            raise

    def create_post(
        self,
        account_id: str,
        location_id: str,
        summary: str,
        media_urls: list[str] | None = None,
        call_to_action: dict[str, str] | None = None,
        event_title: str | None = None,
        event_start_time: datetime | None = None,
        event_end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Google Business Profile に投稿を作成

        Args:
            account_id: Google Business Profile のアカウントID
            location_id: 店舗のロケーションID
            summary: 投稿の説明文（テキスト）
            media_urls: 画像のURLリスト（公開アクセス可能なURL）
            call_to_action: CTA（Call to Action）の辞書
               例: {"actionType": "LEARN_MORE", "url": "https://example.com/booking"}
            event_title: イベントのタイトル（イベント投稿の場合）
            event_start_time: イベント開始時刻（イベント投稿の場合）
            event_end_time: イベント終了時刻（イベント投稿の場合）

        Returns:
            作成された投稿の情報
        """
        try:
            # 投稿リクエストの構築
            post_body = {"summary": summary, "languageCode": "ja"}  # 日本語

            # メディア（画像・動画）の追加
            if media_urls:
                media_items = []
                for media_info in media_urls:
                    # media_infoが辞書の場合は、URLとフォーマットを含む
                    # 文字列の場合は、URLのみ（後方互換性のため）
                    if isinstance(media_info, dict):
                        media_url = media_info.get("url")
                        media_format = media_info.get("format", "PHOTO")  # 'PHOTO' または 'VIDEO'
                    else:
                        # 後方互換性: 文字列の場合はURLとして扱い、拡張子から判定
                        media_url = media_info
                        # URLから拡張子を判定（簡易版）
                        media_format = (
                            "VIDEO"
                            if any(
                                ext in media_url.lower()
                                for ext in [".mp4", ".mov", ".avi", ".webm"]
                            )
                            else "PHOTO"
                        )

                    if media_url:
                        # リソース名（直接アップロードの場合）かURL（GCS経由の場合）かを判定
                        # リソース名の形式: "accounts/.../locations/.../media/..." または "media/..."
                        # URLの形式: "https://..." または "http://..."
                        if media_url.startswith("http://") or media_url.startswith("https://"):
                            # HTTP/HTTPS URLの場合（GCS経由）
                            media_items.append(
                                {"mediaFormat": media_format, "sourceUrl": media_url}
                            )
                        elif "/" in media_url and ("media" in media_url or "accounts" in media_url):
                            # リソース名の場合（直接アップロード）
                            # Google Business Profile APIでは、リソース名を直接指定できる場合がある
                            # ただし、API仕様によってはsourceUrlが必要な場合もあるため、
                            # リソース名をURL形式に変換するか、別のフィールドを使用する
                            # ここでは、リソース名をそのままsourceUrlとして使用（APIが対応している場合）
                            media_items.append(
                                {
                                    "mediaFormat": media_format,
                                    "sourceUrl": media_url,  # リソース名をそのまま使用
                                }
                            )
                        else:
                            # その他の形式（リソース名として扱う）
                            media_items.append(
                                {"mediaFormat": media_format, "sourceUrl": media_url}
                            )
                post_body["media"] = media_items

            # CTAの追加
            if call_to_action:
                post_body["callToAction"] = call_to_action

            # イベント情報の追加（イベント投稿の場合）
            if event_title and event_start_time:
                post_body["event"] = {
                    "title": event_title,
                    "schedule": {
                        "startDate": {
                            "year": event_start_time.year,
                            "month": event_start_time.month,
                            "day": event_start_time.day,
                        },
                        "startTime": {
                            "hours": event_start_time.hour,
                            "minutes": event_start_time.minute,
                        },
                    },
                }
                if event_end_time:
                    post_body["event"]["schedule"]["endDate"] = {
                        "year": event_end_time.year,
                        "month": event_end_time.month,
                        "day": event_end_time.day,
                    }
                    post_body["event"]["schedule"]["endTime"] = {
                        "hours": event_end_time.hour,
                        "minutes": event_end_time.minute,
                    }

            # API呼び出し
            # Google Business Profile API v4: localPosts.create
            # エンドポイント: POST /v4/accounts/{accountId}/locations/{locationId}/localPosts
            parent = f"accounts/{account_id}/locations/{location_id}"
            request = (
                self.service.accounts()
                .locations()
                .localPosts()
                .create(parent=parent, body=post_body)
            )

            result = request.execute()
            logger.info(f"投稿を作成しました: {parent}")
            return result

        except HttpError as e:
            error_details = e.error_details if hasattr(e, "error_details") else str(e)
            logger.error(f"Google Business Profile API エラー: {e.status_code} - {error_details}")
            if e.resp:
                logger.error(f"レスポンス: {e.resp.content}")
            raise
        except Exception as e:
            logger.error(f"投稿作成エラー: {e}")
            raise

    def upload_media_direct(
        self, account_id: str, location_id: str, file_path: str, media_format: str = "PHOTO"
    ) -> str:
        """
        Google Business Profile APIに直接メディアをアップロード

        Args:
            account_id: Google Business Profile のアカウントID
            location_id: 店舗のロケーションID
            file_path: アップロードするファイルのパス
            media_format: メディアフォーマット ('PHOTO' または 'VIDEO')

        Returns:
            アップロードされたメディアのリソース名（URL形式）
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

            # MIMEタイプを判定
            mime_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp",
                ".mp4": "video/mp4",
                ".mov": "video/quicktime",
                ".avi": "video/x-msvideo",
                ".webm": "video/webm",
                ".mkv": "video/x-matroska",
            }

            file_ext = file_path_obj.suffix.lower()
            mime_type = mime_type_map.get(file_ext, "application/octet-stream")

            # メディアフォーマットの検証
            if media_format not in ["PHOTO", "VIDEO"]:
                raise ValueError(
                    f"media_formatは'PHOTO'または'VIDEO'である必要があります: {media_format}"
                )

            parent = f"accounts/{account_id}/locations/{location_id}"

            # Step 1: メディアアップロードリソースを作成
            # Google Business Profile API v4: media.create
            logger.info(f"メディアアップロードリソースを作成中: {parent}")

            # メディアリソースの作成リクエスト
            media_body = {"mediaFormat": media_format}

            try:
                # media.create エンドポイントを呼び出し
                create_request = (
                    self.service.accounts()
                    .locations()
                    .media()
                    .create(parent=parent, body=media_body)
                )
                create_response = create_request.execute()

                # アップロードURLを取得
                upload_url = create_response.get("uploadUrl")
                resource_name = create_response.get("name")

                if not upload_url:
                    # uploadUrlが返されない場合、別の方法を試す
                    # 直接MediaFileUploadを使用してアップロード
                    logger.info("uploadUrlが取得できませんでした。直接アップロードを試行します。")

                    # メディアファイルをアップロード
                    media_upload = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

                    # メディアリソース名を生成（APIが返す形式に合わせる）
                    # 実際のAPIレスポンスに基づいて調整が必要な場合があります
                    upload_request = (
                        self.service.accounts()
                        .locations()
                        .media()
                        .create(parent=parent, body=media_body, media_body=media_upload)
                    )

                    upload_response = None
                    while upload_response is None:
                        status, upload_response = upload_request.next_chunk()
                        if status:
                            logger.debug(f"アップロード進捗: {int(status.progress() * 100)}%")

                    if upload_response:
                        resource_name = upload_response.get("name")
                        logger.info(f"メディアを直接アップロードしました: {resource_name}")
                        return resource_name
                    else:
                        raise ValueError("メディアの直接アップロードに失敗しました。")

            except AttributeError:
                # media()メソッドが存在しない場合、別のAPIエンドポイントを試す
                logger.warning("media.createエンドポイントが見つかりません。代替方法を試行します。")

                # 代替方法: メディアを直接アップロード
                # この場合、GCS経由にフォールバックするか、エラーを返す
                raise NotImplementedError(
                    "Google Business Profile API v4では、メディアの直接アップロードは"
                    "media.createエンドポイントを使用する必要があります。"
                    "APIの仕様を確認してください。"
                )

            # Step 2: アップロードURLにメディアファイルをアップロード
            if upload_url:
                if not REQUESTS_AVAILABLE:
                    raise ImportError(
                        "requestsライブラリが必要です。pip install requests を実行してください。"
                    )

                logger.info(f"メディアファイルをアップロード中: {upload_url}")

                # ファイルを読み込む
                with open(file_path, "rb") as f:
                    file_data = f.read()

                # PUTリクエストでアップロード
                headers = {"Content-Type": mime_type, "Content-Length": str(len(file_data))}

                # 認証ヘッダーを追加
                if self.credentials:
                    self.credentials.refresh(Request())
                    headers["Authorization"] = f"Bearer {self.credentials.token}"

                response = requests.put(upload_url, data=file_data, headers=headers)
                response.raise_for_status()

                logger.info(f"メディアをアップロードしました: {resource_name}")
                return resource_name

            raise ValueError(
                "メディアアップロードに失敗しました。uploadUrlまたはresource_nameが取得できませんでした。"
            )

        except HttpError as e:
            error_details = e.error_details if hasattr(e, "error_details") else str(e)
            logger.error(
                f"Google Business Profile API 直接アップロードエラー: {e.status_code} - {error_details}"
            )
            if e.resp:
                logger.error(f"レスポンス: {e.resp.content}")
            raise
        except Exception as e:
            logger.error(f"メディア直接アップロードエラー: {e}")
            raise

    def upload_media_to_gcs(
        self, file_path: str, bucket_name: str, object_name: str | None = None
    ) -> str:
        """
        画像をGoogle Cloud StorageにアップロードしてURLを取得

        Args:
            file_path: アップロードするファイルのパス
            bucket_name: GCSバケット名
            object_name: オブジェクト名（Noneの場合はファイル名を使用）

        Returns:
            アップロードされたファイルの公開URL
        """
        try:
            from google.cloud import storage

            if object_name is None:
                object_name = Path(file_path).name

            client = storage.Client(credentials=self.credentials)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(object_name)

            blob.upload_from_filename(file_path)

            # 公開URLを取得
            url = blob.public_url
            logger.info(f"画像をGCSにアップロードしました: {url}")
            return url

        except Exception as e:
            logger.error(f"GCSアップロードエラー: {e}")
            raise
