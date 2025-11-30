"""
Instagramストーリー・投稿ダウンロードBot
メインエントリーポイント
"""

import logging
import sys
import time
from pathlib import Path

from .downloader import InstagramDownloader
from .instagram_bot import InstagramBot
from .upload_manager import UploadManager
from .utils import load_companies_from_file, load_config, validate_config

logger = logging.getLogger(__name__)


class InstagramDownloadBot:
    """InstagramダウンロードBotのメインクラス"""

    def __init__(self, config_path: str = "config/config.json"):
        """
        Args:
            config_path: 設定ファイルのパス
        """
        self.config = load_config(config_path)

        if not validate_config(self.config):
            raise ValueError("設定ファイルが無効です")

        # 設定から値を取得（後方互換性のため、既存の設定も保持）
        instagram_config = self.config["instagram"]
        self.username = instagram_config["username"]
        self.password = instagram_config["password"]
        self.session_file = instagram_config["session_file"]
        
        # 複数アカウント設定（7アカウント対応）
        self.instagram_accounts = self.config.get("instagram_accounts", [])
        if not self.instagram_accounts:
            # アカウントが設定されていない場合は、既存の1アカウントを使用
            self.instagram_accounts = [instagram_config]
        
        # セッションIDの重複をチェック（アカウント凍結を防ぐため）
        self._check_and_disable_duplicate_sessions()
        
        # enabledがfalseのアカウントを除外（デフォルトはtrue）
        self.instagram_accounts = [
            account for account in self.instagram_accounts
            if account.get("enabled", True) is not False
        ]

        download_config = self.config["download"]
        self.base_directory = download_config["base_directory"]
        self.organize_by_company = download_config["organize_by_company"]
        self.organize_by_date = download_config["organize_by_date"]
        self.download_posts = download_config["download_posts"]
        self.download_stories = download_config["download_stories"]

        settings = self.config["settings"]
        self.retry_attempts = settings["retry_attempts"]
        self.retry_delay = settings["retry_delay"]
        self.delay_between_requests = settings["delay_between_requests"]

        # ターゲット企業リスト
        # 新しい形式: [{"instagram_id": "...", "stores": [...]}]
        # 旧形式（後方互換性）: ["harebare0819", "lumi_915"]
        companies_config = self.config["targets"]["companies"]
        if companies_config and isinstance(companies_config[0], dict):
            # 新しい形式: オブジェクトのリスト
            self.companies = [
                company.get("instagram_id")
                for company in companies_config
                if company.get("instagram_id")
            ]
            self.companies_config = companies_config  # 完全な設定を保持
        else:
            # 旧形式: 文字列のリスト
            self.companies = companies_config
            self.companies_config = None

        # ダウンロード制限
        self.posts_limit = self.config["targets"]["download_limit"]["posts"]
        self.stories_limit = self.config["targets"]["download_limit"]["stories"]

        # BotとDownloaderのインスタンス（後で初期化）
        self.bot: InstagramBot | None = None
        self.downloader: InstagramDownloader | None = None
        self.upload_manager: UploadManager | None = None

        # アップロード設定
        upload_config = self.config.get("upload", {})
        self.auto_upload = upload_config.get("auto_upload", False)
        self.upload_mock_mode = upload_config.get("mock_mode", True)

        # アップロード開始日時（この日時以降の投稿/ストーリーのみをアップロード）
        self.upload_start_date = None
        start_date_str = upload_config.get("start_date")
        if start_date_str:
            try:
                from datetime import datetime

                self.upload_start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                logger.info(f"アップロード開始日時を設定: {self.upload_start_date}")
            except ValueError:
                logger.warning(
                    f"アップロード開始日時の形式が不正です: {start_date_str} (形式: YYYY-MM-DD HH:MM:SS)"
                )

    def _extract_user_id_from_sessionid(self, sessionid: str) -> str | None:
        """
        セッションIDからユーザーIDを抽出
        
        Args:
            sessionid: セッションID（形式: "ユーザーID%3A..." または "ユーザーID:..."）
            
        Returns:
            ユーザーID、抽出できない場合はNone
        """
        try:
            if "%3A" in sessionid:
                return sessionid.split("%3A")[0]
            elif ":" in sessionid:
                return sessionid.split(":")[0]
            return None
        except:
            return None

    def _check_and_disable_duplicate_sessions(self) -> None:
        """
        セッションIDの重複をチェックし、重複しているアカウントを自動的に無効化
        同じセッションIDで複数のアカウントがログインすると、アカウントが凍結される可能性がある
        """
        import json
        
        # ユーザーID -> [(username, session_file, account_index), ...] のマッピング
        user_id_map: dict[str, list[tuple[str, str, int]]] = {}
        
        for idx, account in enumerate(self.instagram_accounts):
            username = account.get("username", "unknown")
            session_file = account.get("session_file", "")
            
            if not session_file:
                continue
            
            session_path = Path(session_file)
            if not session_path.exists():
                continue
            
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                
                auth_data = session_data.get("authorization_data", {})
                sessionid = auth_data.get("sessionid", "")
                ds_user_id = auth_data.get("ds_user_id", "")
                
                if not sessionid:
                    continue
                
                # ユーザーIDを取得（ds_user_idがあればそれを使用、なければsessionidから抽出）
                user_id = ds_user_id if ds_user_id else self._extract_user_id_from_sessionid(sessionid)
                
                if user_id:
                    if user_id not in user_id_map:
                        user_id_map[user_id] = []
                    user_id_map[user_id].append((username, session_file, idx))
            
            except Exception as e:
                logger.warning(f"セッションファイルの読み込みエラー ({username}): {e}")
                continue
        
        # 重複を検出して、2つ目以降のアカウントを無効化
        duplicates_found = False
        for user_id, accounts_list in user_id_map.items():
            if len(accounts_list) > 1:
                duplicates_found = True
                logger.error(
                    f"⚠️ セッションID重複が検出されました！ "
                    f"ユーザーID {user_id} が {len(accounts_list)} 個のアカウントで使用されています。"
                )
                logger.error("重複しているアカウント:")
                for username, session_file, account_idx in accounts_list:
                    logger.error(f"  - {username} ({session_file})")
                
                # 最初のアカウントは有効のまま、2つ目以降を無効化
                for username, session_file, account_idx in accounts_list[1:]:
                    logger.error(
                        f"⚠️ アカウント凍結を防ぐため、"
                        f"{username} ({session_file}) のログインを無効化します"
                    )
                    self.instagram_accounts[account_idx]["enabled"] = False
        
        if duplicates_found:
            logger.error(
                "⚠️⚠️⚠️ セッションID重複により、一部のアカウントが無効化されました。 "
                "各アカウントは異なるセッションIDを使用する必要があります。 "
                "重複を解決するまで、無効化されたアカウントは使用されません。"
            )

    def initialize(self, verification_code: str | None = None) -> bool:
        """
        Botを初期化（ログイン）

        Args:
            verification_code: 2FA認証コード（必要な場合）

        Returns:
            初期化成功したかどうか
        """
        try:
            logger.info("Botを初期化しています...")

            # InstagramBotを初期化
            self.bot = InstagramBot(self.username, self.password, self.session_file)

            # ログイン
            if not self.bot.login(verification_code):
                logger.error("ログインに失敗しました")
                return False

            # Downloaderを初期化
            self.downloader = InstagramDownloader(
                self.bot.client,
                self.base_directory,
                self.organize_by_company,
                self.organize_by_date,
                self.delay_between_requests,
            )

            # UploadManagerを初期化
            upload_config = self.config.get("upload", {})
            video_conversion_config = upload_config.get("video_conversion", {})
            selenium_config = upload_config.get("selenium", {})
            
            self.upload_manager = UploadManager(
                db_path="data/upload_history.db",
                mock_mode=self.upload_mock_mode,
                mock_delay=0.5,
                start_date=self.upload_start_date,
                location_mapping={},  # 初期化時は空（後で動的に設定）
                video_conversion_enabled=video_conversion_config.get("enabled", True),
                video_min_width=video_conversion_config.get("min_width", 400),
                video_min_height=video_conversion_config.get("min_height", 300),
                use_selenium=selenium_config.get("enabled", False),
                chrome_profile_path=selenium_config.get("chrome_profile_path"),
                profile_name_gbp=selenium_config.get("profile_name_gbp"),
            )

            logger.info("Botの初期化が完了しました")
            return True

        except Exception as e:
            logger.error(f"Botの初期化エラー: {e}")
            return False

    def load_companies_from_file(self, file_path: str) -> None:
        """
        ファイルから企業リストを読み込む

        Args:
            file_path: 企業リストファイルのパス（1行1企業）
        """
        companies = load_companies_from_file(file_path)
        if companies:
            self.companies = companies
            # 設定ファイルも更新
            self.config["targets"]["companies"] = companies
            logger.info(f"企業リストを更新しました: {len(companies)}社")

    def add_company(self, identifier: str) -> None:
        """
        企業を追加

        Args:
            identifier: Instagramのユーザー名（例: "username"）またはユーザーID（例: "123456789"）
        """
        if identifier not in self.companies:
            self.companies.append(identifier)
            self.config["targets"]["companies"] = self.companies
            logger.info(f"企業を追加しました: {identifier}")

    def remove_company(self, identifier: str) -> None:
        """
        企業を削除

        Args:
            identifier: Instagramのユーザー名（例: "username"）またはユーザーID（例: "123456789"）
        """
        if identifier in self.companies:
            self.companies.remove(identifier)
            self.config["targets"]["companies"] = self.companies
            logger.info(f"企業を削除しました: {identifier}")

    def download_for_company(self, identifier: str) -> dict:
        """
        特定の企業のコンテンツをダウンロード

        Args:
            identifier: Instagramのユーザー名（例: "username"）またはユーザーID（例: "123456789"）

        Returns:
            ダウンロード結果の辞書
        """
        if not self.bot or not self.downloader:
            raise RuntimeError("Botが初期化されていません。initialize()を先に呼び出してください")

        import time
        from datetime import datetime

        execution_start = datetime.now()
        execution_start_time = time.time()
        log_id = None

        logger.info(f"企業のダウンロードを開始: {identifier}")

        # 数値のみの場合は既にユーザーIDと判断
        if identifier.isdigit():
            user_id = identifier
            logger.info(f"ユーザーIDとして認識: {identifier}")
        else:
            # config.jsonからユーザーIDを取得（既に保存されている場合）
            user_id = None
            company_config = None
            
            # 新しい形式の設定から該当する企業の設定を探す
            if self.companies_config:
                for company in self.companies_config:
                    if company.get("instagram_id") == identifier:
                        company_config = company
                        user_id = company.get("user_id")
                        break
            
            # ユーザーIDが存在しない場合のみ取得
            if not user_id:
                # ユーザーID取得前に待機時間を設ける（レート制限対策）
                self.bot.wait_between_requests(self.delay_between_requests)
                
                # ユーザーIDを取得（ユーザー名またはユーザーIDのどちらでも対応）
                user_id = self.bot.get_user_id(identifier, delay=0)  # 既に待機時間を設けているのでdelay=0
                
                # ユーザーIDを取得できた場合、config.jsonに保存
                if user_id and company_config is not None:
                    company_config["user_id"] = user_id
                    # config.jsonを保存
                    from .utils import save_config
                    save_config(self.config, "config/config.json")
                    logger.info(f"ユーザーIDをconfig.jsonに保存しました: {identifier} -> {user_id}")
            else:
                logger.info(f"保存済みのユーザーIDを使用します: {identifier} -> {user_id}")
        if not user_id:
            error_msg = f"ユーザーIDの取得に失敗しました: {identifier}"
            logger.error(error_msg)

            # エラーログを記録
            if self.upload_manager:
                self.upload_manager.db.log_execution(
                    execution_type="download",
                    status="failed",
                    message=error_msg,
                    instagram_id=identifier,
                    error_message=error_msg,
                    started_at=execution_start,
                    completed_at=datetime.now(),
                    execution_time_seconds=time.time() - execution_start_time,
                )

            return {"posts": [], "stories": [], "error": "user_id_not_found"}

        # 表示用のユーザー名を取得（ユーザーIDの場合はそのまま使用）
        display_name = identifier if not identifier.isdigit() else user_id

        # ダウンロード実行
        download_error = None
        try:
            results = self.downloader.download_all(
                display_name,
                user_id,
                self.download_posts,
                self.download_stories,
                self.posts_limit,
                self.stories_limit,
            )

            posts_count = len(results.get("posts", []))
            stories_count = len(results.get("stories", []))

            logger.info(
                f"ダウンロード完了: {display_name} "
                f"(投稿: {posts_count}件, "
                f"ストーリー: {stories_count}件)"
            )
        except Exception as e:
            download_error = str(e)
            logger.error(f"ダウンロードエラー: {download_error}")
            results = {"posts": [], "stories": [], "error": download_error}
            posts_count = 0
            stories_count = 0

        # 自動アップロードが有効な場合
        upload_results = {}
        upload_success_count = 0
        upload_failed_count = 0
        upload_skipped_count = 0

        if self.auto_upload and self.upload_manager and not download_error:
            try:
                # GBPロケーション情報を取得
                locations = []  # [{"account_id": "...", "location_id": "..."}, ...]

                # 新しい形式: companiesがオブジェクトのリストの場合
                if self.companies_config:
                    # display_name（instagram_id）に一致する企業設定を検索
                    company_config = None
                    for company in self.companies_config:
                        if company.get("instagram_id") == display_name:
                            company_config = company
                            break

                    if company_config:
                        # google_business_locationsから直接取得
                        locations = company_config.get("google_business_locations", [])

                # 旧形式（後方互換性）: store_mappingを使用
                if not locations:
                    store_mapping = self.config.get("targets", {}).get("store_mapping", {})
                    instagram_config = store_mapping.get(display_name, {})

                    # 旧形式1: {"stores": [{"store_id": "...", "google_business": {...}}]}
                    if isinstance(instagram_config, dict) and "stores" in instagram_config:
                        stores = instagram_config.get("stores", [])
                        for store_config in stores:
                            google_business = store_config.get("google_business", {})
                            if google_business:
                                locations.append(
                                    {
                                        "account_id": google_business.get("account_id"),
                                        "location_id": google_business.get("location_id"),
                                    }
                                )

                # ロケーションマッピングをデータベースに登録
                for location in locations:
                    account_id = location.get("account_id")
                    location_id = location.get("location_id")
                    if account_id and location_id:
                        self.upload_manager.db.add_location_mapping(
                            display_name, account_id, location_id
                        )

                upload_results = {"posts": {}, "stories": {}}

                # 投稿をアップロード
                if results.get("posts") and locations:
                    upload_results["posts"] = self.upload_manager.process_downloaded_posts(
                        display_name, results["posts"], locations=locations
                    )
                    upload_success_count += upload_results["posts"].get("success", 0)
                    upload_failed_count += upload_results["posts"].get("failed", 0)
                    upload_skipped_count += upload_results["posts"].get("skipped", 0)

                # ストーリーをアップロード
                if results.get("stories") and locations:
                    upload_results["stories"] = self.upload_manager.process_downloaded_stories(
                        display_name, results["stories"], locations=locations
                    )
                    upload_success_count += upload_results["stories"].get("success", 0)
                    upload_failed_count += upload_results["stories"].get("failed", 0)
                    upload_skipped_count += upload_results["stories"].get("skipped", 0)

                results["upload"] = upload_results

                logger.info(
                    f"アップロード完了: {display_name} "
                    f"(投稿: {upload_results['posts'].get('success', 0)}件, "
                    f"ストーリー: {upload_results['stories'].get('success', 0)}件)"
                )
            except Exception as e:
                upload_error = str(e)
                logger.error(f"アップロードエラー: {upload_error}")
                upload_failed_count += 1

        # 実行ログを記録
        execution_end = datetime.now()
        execution_time = time.time() - execution_start_time

        if self.upload_manager:
            # 実行タイプを決定
            execution_type = (
                "download_and_upload" if self.auto_upload and upload_results else "download"
            )

            # ステータスを決定
            if download_error:
                status = "failed"
                message = f"ダウンロードエラー: {download_error}"
            elif upload_failed_count > 0:
                status = "partial_success"
                message = f"ダウンロード成功、アップロード一部失敗 (成功: {upload_success_count}, 失敗: {upload_failed_count}, スキップ: {upload_skipped_count})"
            elif upload_success_count > 0 or upload_skipped_count > 0:
                status = "success"
                message = f"処理完了 (投稿: {posts_count}件, ストーリー: {stories_count}件, アップロード成功: {upload_success_count}, スキップ: {upload_skipped_count})"
            elif posts_count > 0 or stories_count > 0:
                status = "success"
                message = f"ダウンロード完了 (投稿: {posts_count}件, ストーリー: {stories_count}件)"
            else:
                status = "success"
                message = "処理完了（ダウンロード対象なし）"

            # 詳細情報を準備
            details = {
                "download": {
                    "posts_count": posts_count,
                    "stories_count": stories_count,
                    "posts_files": len(results.get("posts", [])),
                    "stories_files": len(results.get("stories", [])),
                }
            }

            if upload_results:
                details["upload"] = {
                    "posts": {
                        "total": upload_results.get("posts", {}).get("total", 0),
                        "success": upload_results.get("posts", {}).get("success", 0),
                        "failed": upload_results.get("posts", {}).get("failed", 0),
                        "skipped": upload_results.get("posts", {}).get("skipped", 0),
                    },
                    "stories": {
                        "total": upload_results.get("stories", {}).get("total", 0),
                        "success": upload_results.get("stories", {}).get("success", 0),
                        "failed": upload_results.get("stories", {}).get("failed", 0),
                        "skipped": upload_results.get("stories", {}).get("skipped", 0),
                    },
                }

            log_id = self.upload_manager.db.log_execution(
                execution_type=execution_type,
                status=status,
                message=message,
                instagram_id=display_name,
                details=details,
                posts_count=posts_count,
                stories_count=stories_count,
                success_count=upload_success_count,
                failed_count=upload_failed_count,
                skipped_count=upload_skipped_count,
                error_message=download_error,
                execution_time_seconds=execution_time,
                started_at=execution_start,
                completed_at=execution_end,
            )

            results["log_id"] = log_id

        return results

    def download_all_companies(self) -> dict:
        """
        すべての企業のコンテンツをダウンロード（7アカウントでローテーション処理）

        Returns:
            全企業のダウンロード結果の辞書
        """
        logger.info(f"全企業のダウンロードを開始: {len(self.companies)}社")
        logger.info(f"使用アカウント数: {len(self.instagram_accounts)}アカウント")

        all_results = {}
        success_count = 0
        error_count = 0
        
        # 7アカウントでローテーション処理
        num_accounts = len(self.instagram_accounts)
        companies_per_account_batch = 5  # 1アカウントあたり5社ずつ処理
        
        # 各アカウントが処理する企業を分散（ループ方式）
        # アカウント1: 0, 7, 14, 21... アカウント2: 1, 8, 15, 22...
        account_company_indices = [[] for _ in range(num_accounts)]
        for i in range(len(self.companies)):
            account_idx = i % num_accounts
            account_company_indices[account_idx].append(i)
        
        # 各アカウントの処理済み企業数を追跡
        account_processed_counts = [0] * num_accounts
        # 失敗したアカウントを追跡（再試行しない）
        failed_accounts = set()
        total_processed = 0
        current_account_idx = 0
        current_account_initialized = None  # 現在初期化されているアカウントのインデックス
        reassignment_occurred = False  # 再割り当てが発生したかどうかを追跡
        
        while total_processed < len(self.companies):
            # 現在のアカウントで処理する企業を取得
            account = self.instagram_accounts[current_account_idx]
            account_company_list = account_company_indices[current_account_idx]
            
            # このアカウントで処理する企業のインデックス（5社ずつ）
            start_idx = account_processed_counts[current_account_idx]
            end_idx = min(start_idx + companies_per_account_batch, len(account_company_list))
            
            if start_idx >= len(account_company_list):
                # このアカウントの処理が完了したら、次のアカウントへ
                current_account_idx = (current_account_idx + 1) % num_accounts
                continue
            
            # 失敗したアカウントの場合は、そのアカウントの企業を他のアカウントに再割り当て
            if current_account_idx in failed_accounts:
                logger.warning(f"アカウント{current_account_idx + 1}は失敗済みです。残りの企業を他のアカウントに再割り当てします")
                # このアカウントの残りの企業を他の利用可能なアカウントに再割り当て
                remaining_companies = account_company_list[start_idx:]
                if remaining_companies:
                    # 利用可能なアカウントを探す
                    available_account_idx = None
                    for i in range(num_accounts):
                        if i not in failed_accounts and i != current_account_idx:
                            available_account_idx = i
                            break
                    
                    if available_account_idx is not None:
                        # 他のアカウントに再割り当て
                        logger.info(f"アカウント{available_account_idx + 1}に{len(remaining_companies)}社を再割り当てします")
                        account_company_indices[available_account_idx].extend(remaining_companies)
                        # 再割り当て先のアカウントが既に処理済みの場合、初期化をリセットして再初期化する
                        if account_processed_counts[available_account_idx] >= len(account_company_indices[available_account_idx]) - len(remaining_companies):
                            # 再割り当て先のアカウントが既に処理を完了している場合、初期化をリセット
                            if current_account_initialized == available_account_idx:
                                current_account_initialized = None
                                logger.info(f"アカウント{available_account_idx + 1}は既に処理済みでした。再初期化が必要です")
                    else:
                        # 利用可能なアカウントがない場合はエラーとして記録
                        logger.error("利用可能なアカウントがありません。残りの企業をエラーとして記録します")
                        for company_idx in remaining_companies:
                            company = self.companies[company_idx]
                            all_results[company] = {"error": "アカウント初期化失敗（利用可能なアカウントなし）"}
                            error_count += 1
                            total_processed += 1
                    
                    account_processed_counts[current_account_idx] = len(account_company_list)
                
                current_account_idx = (current_account_idx + 1) % num_accounts
                continue
            
            # アカウントを切り替える場合は、新しいアカウントで初期化
            # 再割り当てされた企業を処理する場合も、アカウントが初期化されていない場合は再初期化が必要
            if current_account_initialized != current_account_idx or self.bot is None or self.downloader is None:
                # アカウントが無効化されているかチェック（セッションID重複など）
                if account.get("enabled", True) is False:
                    logger.error(
                        f"⚠️ アカウント{current_account_idx + 1} ({account['username']}) は無効化されています。 "
                        "セッションID重複などの理由により、ログインをスキップします。"
                    )
                    # このアカウントを失敗リストに追加
                    failed_accounts.add(current_account_idx)
                    # このアカウントの残りの企業を他のアカウントに再割り当て
                    remaining_companies = account_company_list[start_idx:]
                    if remaining_companies:
                        # 利用可能なアカウントを探す
                        available_account_idx = None
                        for i in range(num_accounts):
                            if i not in failed_accounts and i != current_account_idx:
                                available_account_idx = i
                                break
                        
                        if available_account_idx is not None:
                            # 他のアカウントに再割り当て
                            logger.info(f"アカウント{available_account_idx + 1}に{len(remaining_companies)}社を再割り当てします")
                            account_company_indices[available_account_idx].extend(remaining_companies)
                            # 再割り当て先のアカウントが既に処理済みの場合、初期化をリセットして再初期化する
                            if account_processed_counts[available_account_idx] >= len(account_company_indices[available_account_idx]) - len(remaining_companies):
                                # 再割り当て先のアカウントが既に処理を完了している場合、初期化をリセット
                                if current_account_initialized == available_account_idx:
                                    current_account_initialized = None
                                    logger.info(f"アカウント{available_account_idx + 1}は既に処理済みでした。再初期化が必要です")
                        else:
                            # 利用可能なアカウントがない場合はエラーとして記録
                            logger.error("利用可能なアカウントがありません。残りの企業をエラーとして記録します")
                            for company_idx in remaining_companies:
                                company = self.companies[company_idx]
                                all_results[company] = {"error": "アカウント無効化（セッションID重複）"}
                                error_count += 1
                                total_processed += 1
                        
                        account_processed_counts[current_account_idx] = len(account_company_list)
                    
                    current_account_idx = (current_account_idx + 1) % num_accounts
                    continue
                
                logger.info(f"アカウント{current_account_idx + 1}でログイン: {account['username']}")
                
                # 既存のBotがあればクリア
                self.bot = None
                self.downloader = None
                
                # 新しいアカウントで初期化
                self.username = account["username"]
                self.password = account["password"]
                self.session_file = account["session_file"]
                
                if not self.initialize():
                    logger.warning(
                        f"アカウント{current_account_idx + 1} ({account['username']}) の初期化に失敗しました。"
                        "チャレンジ認証が必要な可能性があります。このアカウントをスキップして、次のアカウントで処理を続行します。"
                    )
                    # このアカウントを失敗リストに追加
                    failed_accounts.add(current_account_idx)
                    # このアカウントの残りの企業を他のアカウントに再割り当て
                    remaining_companies = account_company_list[start_idx:]
                    if remaining_companies:
                        # 利用可能なアカウントを探す
                        available_account_idx = None
                        for i in range(num_accounts):
                            if i not in failed_accounts and i != current_account_idx:
                                available_account_idx = i
                                break
                        
                        if available_account_idx is not None:
                            # 他のアカウントに再割り当て
                            logger.info(f"アカウント{available_account_idx + 1}に{len(remaining_companies)}社を再割り当てします")
                            account_company_indices[available_account_idx].extend(remaining_companies)
                            # 再割り当て先のアカウントが既に処理済みの場合、初期化をリセットして再初期化する
                            if account_processed_counts[available_account_idx] >= len(account_company_indices[available_account_idx]) - len(remaining_companies):
                                # 再割り当て先のアカウントが既に処理を完了している場合、初期化をリセット
                                if current_account_initialized == available_account_idx:
                                    current_account_initialized = None
                                    logger.info(f"アカウント{available_account_idx + 1}は既に処理済みでした。再初期化が必要です")
                        else:
                            # 利用可能なアカウントがない場合はエラーとして記録
                            logger.error("利用可能なアカウントがありません。残りの企業をエラーとして記録します")
                            for company_idx in remaining_companies:
                                company = self.companies[company_idx]
                                all_results[company] = {"error": "アカウント初期化失敗（利用可能なアカウントなし）"}
                                error_count += 1
                                total_processed += 1
                        
                        account_processed_counts[current_account_idx] = len(account_company_list)
                    
                    current_account_idx = (current_account_idx + 1) % num_accounts
                    continue
                
                current_account_initialized = current_account_idx
            
            # Botが初期化されているか確認（再割り当てされた企業を処理する場合など）
            if self.bot is None or self.downloader is None:
                logger.warning(f"アカウント{current_account_idx + 1}が初期化されていません。再初期化します")
                if not self.initialize():
                    logger.warning(
                        f"アカウント{current_account_idx + 1} ({self.username}) の再初期化に失敗しました。"
                        "チャレンジ認証が必要な可能性があります。このアカウントをスキップして、次のアカウントで処理を続行します。"
                    )
                    failed_accounts.add(current_account_idx)
                    # 残りの企業を他のアカウントに再割り当て
                    remaining_companies = account_company_list[start_idx:]
                    if remaining_companies:
                        available_account_idx = None
                        for i in range(num_accounts):
                            if i not in failed_accounts and i != current_account_idx:
                                available_account_idx = i
                                break
                        
                        if available_account_idx is not None:
                            logger.info(f"アカウント{available_account_idx + 1}に{len(remaining_companies)}社を再割り当てします")
                            account_company_indices[available_account_idx].extend(remaining_companies)
                            if current_account_initialized == available_account_idx:
                                pass
                            else:
                                current_account_initialized = None
                        else:
                            logger.error("利用可能なアカウントがありません。残りの企業をエラーとして記録します")
                            for company_idx in remaining_companies:
                                company = self.companies[company_idx]
                                all_results[company] = {"error": "アカウント初期化失敗（利用可能なアカウントなし）"}
                                error_count += 1
                                total_processed += 1
                        
                        account_processed_counts[current_account_idx] = len(account_company_list)
                    
                    current_account_idx = (current_account_idx + 1) % num_accounts
                    continue
            
            # このアカウントで処理する企業を処理
            companies_to_process = account_company_list[start_idx:end_idx]
            
            for company_idx in companies_to_process:
                company = self.companies[company_idx]
                global_idx = total_processed + 1
                
                try:
                    logger.info(f"[{global_idx}/{len(self.companies)}] アカウント{current_account_idx + 1}で処理中: {company}")

                    results = self.download_for_company(company)
                    all_results[company] = results

                    # レート制限エラー（feedback_required）をチェック
                    error_msg = results.get("error", "")
                    if error_msg and "feedback_required" in error_msg.lower():
                        logger.error(f"アカウント{current_account_idx + 1}でレート制限エラーが発生しました: {company}")
                        # 元のアカウントインデックスを保持
                        failed_account_idx = current_account_idx
                        # このアカウントを失敗リストに追加
                        failed_accounts.add(failed_account_idx)
                        # このアカウントの残りの企業を他のアカウントに再割り当て
                        remaining_companies = account_company_list[account_processed_counts[failed_account_idx]:]
                        if remaining_companies:
                            # 利用可能なアカウントを探す
                            available_account_idx = None
                            for i in range(num_accounts):
                                if i not in failed_accounts and i != failed_account_idx:
                                    available_account_idx = i
                                    break
                            
                            if available_account_idx is not None:
                                # 他のアカウントに再割り当て
                                logger.info(f"アカウント{available_account_idx + 1}に{len(remaining_companies)}社を再割り当てします")
                                account_company_indices[available_account_idx].extend(remaining_companies)
                                # 再割り当て先のアカウントが既に処理済みの場合、初期化をリセット
                                if account_processed_counts[available_account_idx] >= len(account_company_indices[available_account_idx]) - len(remaining_companies):
                                    if current_account_initialized == available_account_idx:
                                        current_account_initialized = None
                                        logger.info(f"アカウント{available_account_idx + 1}は既に処理済みでした。再初期化が必要です")
                                # 再割り当て先のアカウントに切り替えて処理を継続
                                current_account_idx = available_account_idx
                            else:
                                logger.error("利用可能なアカウントがありません。残りの企業をエラーとして記録します")
                                for remaining_company_idx in remaining_companies:
                                    remaining_company = self.companies[remaining_company_idx]
                                    all_results[remaining_company] = {"error": "レート制限エラー（利用可能なアカウントなし）"}
                                    error_count += 1
                                    total_processed += 1
                                # 利用可能なアカウントがない場合、次のアカウントへ
                                current_account_idx = (failed_account_idx + 1) % num_accounts
                            
                            # 元のアカウントの処理済みカウントを更新
                            account_processed_counts[failed_account_idx] = len(account_company_list)
                        
                        # 初期化をリセット
                        current_account_initialized = None
                        self.bot = None
                        self.downloader = None
                        # 再割り当てが発生したことを記録
                        reassignment_occurred = True
                        break  # このアカウントの処理を中断（再割り当て先のアカウントで処理を継続）

                    if "error" not in results:
                        success_count += 1
                    else:
                        error_count += 1

                    # 企業間の待機時間
                    if global_idx < len(self.companies):
                        self.bot.wait_between_requests(self.delay_between_requests)

                except Exception as e:
                    logger.error(f"企業のダウンロードエラー ({company}): {e}")
                    all_results[company] = {"error": str(e)}
                    error_count += 1
                
                total_processed += 1
                account_processed_counts[current_account_idx] += 1
            
            # 5社処理したら、次のアカウントに切り替え
            # ただし、再割り当てが発生した場合は、再割り当て先のアカウントで処理を継続するため、ここでは切り替えない
            if not reassignment_occurred:
                current_account_idx = (current_account_idx + 1) % num_accounts
            else:
                # 再割り当てが発生した場合は、フラグをリセットしてwhileループの最初に戻る
                reassignment_occurred = False
            
            # アカウント切り替え時の待機時間
            if total_processed < len(self.companies):
                time.sleep(self.delay_between_requests * 2)  # アカウント切り替え時は少し長めに待機

        logger.info(f"全企業のダウンロード完了: 成功 {success_count}社, 失敗 {error_count}社")

        return all_results


def main():
    """メイン関数"""
    try:
        # Botを初期化
        bot = InstagramDownloadBot("config/config.json")

        # 企業リストファイルが指定されている場合は読み込む
        # 例: companies.txt ファイルから読み込む場合
        companies_file = Path("companies.txt")
        if companies_file.exists():
            bot.load_companies_from_file(str(companies_file))

        # 7アカウント対応後は、download_all_companies()内で各アカウントを個別に初期化するため、
        # 最初の初期化は不要（複数アカウントが設定されている場合はスキップ）
        if not bot.instagram_accounts or len(bot.instagram_accounts) == 1:
            # 単一アカウントの場合のみ初期化
            if not bot.initialize():
                logger.error(
                    "Botの初期化に失敗しました。チャレンジ認証が必要な可能性があります。"
                    "セッション情報を更新する場合は、scripts/extract_session_from_browser.py を使用してください。"
                )
                sys.exit(1)

        # すべての企業のコンテンツをダウンロード
        results = bot.download_all_companies()

        # 結果サマリーを表示
        print("\n=== ダウンロード結果サマリー ===")
        for company, result in results.items():
            if "error" in result:
                print(f"{company}: エラー - {result['error']}")
            else:
                posts_count = len(result.get("posts", []))
                stories_count = len(result.get("stories", []))
                upload_info = ""
                if result.get("upload"):
                    upload_posts = result["upload"].get("posts", {})
                    upload_stories = result["upload"].get("stories", {})
                    if upload_posts or upload_stories:
                        upload_info = f" (アップロード: 投稿{upload_posts.get('success', 0)}件, ストーリー{upload_stories.get('success', 0)}件)"
                print(f"{company}: 投稿 {posts_count}件, ストーリー {stories_count}件{upload_info}")

        logger.info("すべての処理が完了しました")

        # 実行ログレポートを表示（オプション）
        try:
            from scripts.log_viewer import LogViewer

            log_viewer = LogViewer()
            print("\n" + "=" * 60)
            print("実行ログレポート（最近の実行）")
            print("=" * 60)
            log_viewer.print_client_report(days=7, limit=10)
        except Exception as e:
            logger.debug(f"ログレポート表示エラー: {e}")

        # アップロードログレポートを表示（モックモードの場合）
        try:
            from scripts.upload_log_viewer import UploadLogViewer

            upload_log_viewer = UploadLogViewer()
            if bot.auto_upload and bot.upload_manager and bot.upload_manager.mock_mode:
                print("\n" + "=" * 60)
                print("アップロードログレポート（モック）")
                print("=" * 60)
                upload_log_viewer.print_client_report(limit=10)
        except Exception as e:
            logger.debug(f"アップロードログレポート表示エラー: {e}")

    except KeyboardInterrupt:
        logger.info("ユーザーによって中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
