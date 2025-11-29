"""
データベース管理モジュール
アップロード履歴を管理して重複を防ぐ
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class UploadDatabase:
    """アップロード履歴を管理するデータベース"""

    def __init__(self, db_path: str = "data/upload_history.db"):
        """
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """データベースとテーブルを初期化"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # インスタIDとGBPロケーションのマッピングテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS instagram_location_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instagram_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(instagram_id, account_id, location_id)
                )
            """
            )

            # 投稿アップロード履歴テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
                    instagram_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    taken_at TIMESTAMP NOT NULL,
                    file_path TEXT NOT NULL,
                    upload_status TEXT NOT NULL DEFAULT 'pending',
                    upload_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(taken_at, instagram_id, location_id)
                )
            """
            )

            # ストーリーアップロード履歴テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_stories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    story_id TEXT,
                    instagram_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    taken_at TIMESTAMP NOT NULL,
                    file_path TEXT NOT NULL,
                    upload_status TEXT NOT NULL DEFAULT 'pending',
                    upload_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(taken_at, instagram_id, location_id)
                )
            """
            )

            # インデックスを作成（検索速度向上）
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_posts_taken_at 
                ON uploaded_posts(taken_at, instagram_id, location_id)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stories_taken_at 
                ON uploaded_stories(taken_at, instagram_id, location_id)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mapping_instagram_id 
                ON instagram_location_mapping(instagram_id)
            """
            )

            # 実行ログテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_type TEXT NOT NULL,
                    instagram_id TEXT,
                    account_id TEXT,
                    location_id TEXT,
                    status TEXT NOT NULL,
                    message TEXT,
                    details TEXT,
                    posts_count INTEGER DEFAULT 0,
                    stories_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    skipped_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    execution_time_seconds REAL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 既存のテーブルに location_id カラムを追加（マイグレーション）
            # execution_logs テーブル
            try:
                cursor.execute("ALTER TABLE execution_logs ADD COLUMN location_id TEXT")
            except sqlite3.OperationalError:
                pass  # カラムが既に存在する場合はスキップ

            # uploaded_posts テーブルから account_id を削除（マイグレーション）
            # SQLiteでは直接DROP COLUMNできないため、テーブルを再作成
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploaded_posts'")
                if cursor.fetchone():
                    # 既存のテーブルにaccount_idカラムがあるか確認
                    cursor.execute("PRAGMA table_info(uploaded_posts)")
                    columns = [row[1] for row in cursor.fetchall()]
                    has_account_id = "account_id" in columns
                    
                    if has_account_id:
                        # 既存の一時テーブルを削除（前回のマイグレーションが失敗した場合）
                        cursor.execute("DROP TABLE IF EXISTS uploaded_posts_new")
                        # 既存のテーブルがある場合、account_idカラムを削除するために再作成
                        cursor.execute("""
                            CREATE TABLE uploaded_posts_new (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                post_id TEXT,
                                instagram_id TEXT NOT NULL,
                                location_id TEXT NOT NULL,
                                taken_at TIMESTAMP NOT NULL,
                                file_path TEXT NOT NULL,
                                upload_status TEXT NOT NULL DEFAULT 'pending',
                                upload_date TIMESTAMP,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(taken_at, instagram_id, location_id)
                            )
                        """)
                        # 既存データをコピー（account_idを除外、location_idがNULLのレコードは除外）
                        cursor.execute("""
                            INSERT INTO uploaded_posts_new 
                            (id, post_id, instagram_id, location_id, taken_at, file_path, upload_status, upload_date, created_at)
                            SELECT id, post_id, instagram_id, location_id, taken_at, file_path, upload_status, upload_date, created_at
                            FROM uploaded_posts
                            WHERE location_id IS NOT NULL
                        """)
                        cursor.execute("DROP TABLE uploaded_posts")
                        cursor.execute("ALTER TABLE uploaded_posts_new RENAME TO uploaded_posts")
                        # インデックスを再作成
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_posts_taken_at 
                            ON uploaded_posts(taken_at, instagram_id, location_id)
                        """)
            except sqlite3.OperationalError as e:
                logger.warning(f"uploaded_posts テーブルのマイグレーションエラー: {e}")

            # uploaded_stories テーブルから account_id を削除（マイグレーション）
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='uploaded_stories'")
                if cursor.fetchone():
                    # 既存のテーブルにaccount_idカラムがあるか確認
                    cursor.execute("PRAGMA table_info(uploaded_stories)")
                    columns = [row[1] for row in cursor.fetchall()]
                    has_account_id = "account_id" in columns
                    
                    if has_account_id:
                        # 既存の一時テーブルを削除（前回のマイグレーションが失敗した場合）
                        cursor.execute("DROP TABLE IF EXISTS uploaded_stories_new")
                        # 既存のテーブルがある場合、account_idカラムを削除するために再作成
                        cursor.execute("""
                            CREATE TABLE uploaded_stories_new (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                story_id TEXT,
                                instagram_id TEXT NOT NULL,
                                location_id TEXT NOT NULL,
                                taken_at TIMESTAMP NOT NULL,
                                file_path TEXT NOT NULL,
                                upload_status TEXT NOT NULL DEFAULT 'pending',
                                upload_date TIMESTAMP,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(taken_at, instagram_id, location_id)
                            )
                        """)
                        # 既存データをコピー（account_idを除外、location_idがNULLのレコードは除外）
                        cursor.execute("""
                            INSERT INTO uploaded_stories_new 
                            (id, story_id, instagram_id, location_id, taken_at, file_path, upload_status, upload_date, created_at)
                            SELECT id, story_id, instagram_id, location_id, taken_at, file_path, upload_status, upload_date, created_at
                            FROM uploaded_stories
                            WHERE location_id IS NOT NULL
                        """)
                        cursor.execute("DROP TABLE uploaded_stories")
                        cursor.execute("ALTER TABLE uploaded_stories_new RENAME TO uploaded_stories")
                        # インデックスを再作成
                        cursor.execute("""
                            CREATE INDEX IF NOT EXISTS idx_stories_taken_at 
                            ON uploaded_stories(taken_at, instagram_id, location_id)
                        """)
            except sqlite3.OperationalError as e:
                logger.warning(f"uploaded_stories テーブルのマイグレーションエラー: {e}")

            # 実行ログのインデックス
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_logs_execution_type 
                ON execution_logs(execution_type, started_at DESC)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_logs_instagram_id 
                ON execution_logs(instagram_id, started_at DESC)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_logs_status 
                ON execution_logs(status, started_at DESC)
            """
            )

            conn.commit()
            conn.close()
            logger.info(f"データベースを初期化しました: {self.db_path}")

        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
            raise

    def add_location_mapping(self, instagram_id: str, account_id: str, location_id: str) -> bool:
        """
        Instagram IDとGBPロケーションのマッピングを追加

        Args:
            instagram_id: Instagramのユーザー名（例: "harebare0819"）または数値ID（例: "68343678457"）
            account_id: Google Business Profile のアカウントID
            location_id: Google Business Profile のロケーションID

        Returns:
            追加成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO instagram_location_mapping
                (instagram_id, account_id, location_id)
                VALUES (?, ?, ?)
            """,
                (instagram_id, account_id, location_id),
            )

            conn.commit()
            conn.close()

            logger.info(
                f"ロケーションマッピングを追加: {instagram_id} -> {account_id}/{location_id}"
            )
            return True

        except Exception as e:
            logger.error(f"ロケーションマッピング追加エラー: {e}")
            return False

    def get_locations(self, instagram_id: str) -> list[dict[str, str]]:
        """
        Instagram IDに紐づくGBPロケーションのリストを取得

        Args:
            instagram_id: Instagramのユーザー名（例: "harebare0819"）または数値ID（例: "68343678457"）

        Returns:
            ロケーション情報のリスト [{"account_id": "...", "location_id": "..."}, ...]
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT account_id, location_id FROM instagram_location_mapping
                WHERE instagram_id = ?
            """,
                (instagram_id,),
            )

            locations = [{"account_id": row[0], "location_id": row[1]} for row in cursor.fetchall()]
            conn.close()

            return locations

        except Exception as e:
            logger.error(f"ロケーション取得エラー: {e}")
            return []

    # 後方互換性のためのメソッド（非推奨）
    def add_store_mapping(
        self, instagram_id: str, store_id: str, store_name: str | None = None
    ) -> bool:
        """後方互換性のためのメソッド（非推奨）"""
        logger.warning("add_store_mappingは非推奨です。add_location_mappingを使用してください。")
        return False

    def get_store_ids(self, instagram_id: str) -> list[str]:
        """後方互換性のためのメソッド（非推奨）"""
        logger.warning("get_store_idsは非推奨です。get_locationsを使用してください。")
        return []

    def get_all_mappings(self) -> list[dict[str, Any]]:
        """
        すべてのインスタIDと店舗IDのマッピングを取得

        Returns:
            マッピング情報のリスト
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM instagram_store_mapping")
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"マッピング取得エラー: {e}")
            return []

    def is_post_uploaded(
        self, taken_at: datetime, instagram_id: str, location_id: str
    ) -> bool:
        """
        投稿が既にアップロードされているかチェック（日時ベース）

        Args:
            taken_at: 投稿のアップロード日時
            instagram_id: Instagramのユーザー名またはID
            location_id: Google Business Profile のロケーションID

        Returns:
            アップロード済みの場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) FROM uploaded_posts
                WHERE taken_at = ? AND instagram_id = ? AND location_id = ? 
                AND upload_status = 'success'
            """,
                (taken_at, instagram_id, location_id),
            )

            count = cursor.fetchone()[0]
            conn.close()

            return count > 0

        except Exception as e:
            logger.error(f"投稿アップロードチェックエラー: {e}")
            return False

    def is_story_uploaded(
        self, taken_at: datetime, instagram_id: str, location_id: str
    ) -> bool:
        """
        ストーリーが既にアップロードされているかチェック（日時ベース）

        Args:
            taken_at: ストーリーのアップロード日時
            instagram_id: Instagramのユーザー名またはID
            location_id: Google Business Profile のロケーションID

        Returns:
            アップロード済みの場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) FROM uploaded_stories
                WHERE taken_at = ? AND instagram_id = ? AND location_id = ? 
                AND upload_status = 'success'
            """,
                (taken_at, instagram_id, location_id),
            )

            count = cursor.fetchone()[0]
            conn.close()

            return count > 0

        except Exception as e:
            logger.error(f"ストーリーアップロードチェックエラー: {e}")
            return False

    def record_post_upload(
        self,
        taken_at: datetime,
        instagram_id: str,
        location_id: str,
        file_path: str,
        post_id: str | None = None,
        upload_status: str = "success",
        upload_date: datetime | None = None,
    ) -> bool:
        """
        投稿のアップロード履歴を記録（日時ベース）

        Args:
            taken_at: 投稿のアップロード日時
            instagram_id: Instagramのユーザー名またはID
            location_id: Google Business Profile のロケーションID
            file_path: ファイルパス
            post_id: 投稿ID（オプション）
            upload_status: アップロードステータス ('pending', 'success', 'failed')
            upload_date: アップロード日時（Noneの場合は現在時刻）

        Returns:
            記録成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if upload_date is None:
                upload_date = datetime.now()

            # 既存レコードがある場合は更新、ない場合は挿入
            cursor.execute(
                """
                INSERT OR REPLACE INTO uploaded_posts
                (taken_at, instagram_id, location_id, file_path, post_id, upload_status, upload_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    taken_at,
                    instagram_id,
                    location_id,
                    file_path,
                    post_id,
                    upload_status,
                    upload_date,
                ),
            )

            conn.commit()
            conn.close()

            logger.debug(
                f"投稿アップロード履歴を記録: {taken_at} ({instagram_id}, {location_id})"
            )
            return True

        except Exception as e:
            logger.error(f"投稿アップロード履歴記録エラー: {e}")
            return False

    def record_story_upload(
        self,
        taken_at: datetime,
        instagram_id: str,
        location_id: str,
        file_path: str,
        story_id: str | None = None,
        upload_status: str = "success",
        upload_date: datetime | None = None,
    ) -> bool:
        """
        ストーリーのアップロード履歴を記録（日時ベース）

        Args:
            taken_at: ストーリーのアップロード日時
            instagram_id: Instagramのユーザー名またはID
            location_id: Google Business Profile のロケーションID
            file_path: ファイルパス
            story_id: ストーリーID（オプション）
            upload_status: アップロードステータス ('pending', 'success', 'failed')
            upload_date: アップロード日時（Noneの場合は現在時刻）

        Returns:
            記録成功した場合True
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if upload_date is None:
                upload_date = datetime.now()

            # 既存レコードがある場合は更新、ない場合は挿入
            cursor.execute(
                """
                INSERT OR REPLACE INTO uploaded_stories
                (taken_at, instagram_id, location_id, file_path, story_id, upload_status, upload_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    taken_at,
                    instagram_id,
                    location_id,
                    file_path,
                    story_id,
                    upload_status,
                    upload_date,
                ),
            )

            conn.commit()
            conn.close()

            logger.debug(
                f"ストーリーアップロード履歴を記録: {taken_at} ({instagram_id}, {location_id})"
            )
            return True

        except Exception as e:
            logger.error(f"ストーリーアップロード履歴記録エラー: {e}")
            return False

    def get_uploaded_posts(
        self,
        instagram_id: str | None = None,
        location_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        アップロード済み投稿の一覧を取得

        Args:
            instagram_id: Instagramのユーザー名またはID（Noneの場合は全ユーザー）
            location_id: Google Business Profile のロケーションID（Noneの場合は全ロケーション）

        Returns:
            アップロード履歴のリスト
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            conditions = []
            params = []

            if instagram_id:
                conditions.append("instagram_id = ?")
                params.append(instagram_id)
            if location_id:
                conditions.append("location_id = ?")
                params.append(location_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(
                f"""
                SELECT * FROM uploaded_posts
                WHERE {where_clause}
                ORDER BY upload_date DESC
            """,
                params,
            )

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"アップロード済み投稿取得エラー: {e}")
            return []

    def get_uploaded_stories(
        self,
        instagram_id: str | None = None,
        location_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        アップロード済みストーリーの一覧を取得

        Args:
            instagram_id: Instagramのユーザー名またはID（Noneの場合は全ユーザー）
            location_id: Google Business Profile のロケーションID（Noneの場合は全ロケーション）

        Returns:
            アップロード履歴のリスト
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            conditions = []
            params = []

            if instagram_id:
                conditions.append("instagram_id = ?")
                params.append(instagram_id)
            if location_id:
                conditions.append("location_id = ?")
                params.append(location_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(
                f"""
                SELECT * FROM uploaded_stories
                WHERE {where_clause}
                ORDER BY upload_date DESC
            """,
                params,
            )

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"アップロード済みストーリー取得エラー: {e}")
            return []

    def get_upload_statistics(self) -> dict[str, Any]:
        """
        アップロード統計情報を取得

        Returns:
            統計情報の辞書
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 投稿統計
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN upload_status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN upload_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN upload_status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM uploaded_posts
            """
            )
            post_stats = dict(zip(["total", "success", "failed", "pending"], cursor.fetchone()))

            # ストーリー統計
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN upload_status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN upload_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN upload_status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM uploaded_stories
            """
            )
            story_stats = dict(zip(["total", "success", "failed", "pending"], cursor.fetchone()))

            conn.close()

            return {"posts": post_stats, "stories": story_stats}

        except Exception as e:
            logger.error(f"アップロード統計取得エラー: {e}")
            return {"posts": {}, "stories": {}}

    def log_execution(
        self,
        execution_type: str,
        status: str,
        message: str = "",
        instagram_id: str | None = None,
        account_id: str | None = None,
        location_id: str | None = None,
        details: dict[str, Any] | None = None,
        posts_count: int = 0,
        stories_count: int = 0,
        success_count: int = 0,
        failed_count: int = 0,
        skipped_count: int = 0,
        error_message: str | None = None,
        execution_time_seconds: float | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> int:
        """
        実行ログを記録

        Args:
            execution_type: 実行タイプ ('download', 'upload', 'download_and_upload' など)
            status: 実行ステータス ('success', 'failed', 'partial_success' など)
            message: ログメッセージ
            instagram_id: Instagramのユーザー名またはID
            account_id: Google Business Profile アカウントID
            location_id: Google Business Profile ロケーションID
            details: 詳細情報（JSON形式で保存）
            posts_count: 処理した投稿数
            stories_count: 処理したストーリー数
            success_count: 成功件数
            failed_count: 失敗件数
            skipped_count: スキップ件数
            error_message: エラーメッセージ
            execution_time_seconds: 実行時間（秒）
            started_at: 開始日時（Noneの場合は現在時刻）
            completed_at: 完了日時（Noneの場合は現在時刻）

        Returns:
            記録されたログのID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if started_at is None:
                started_at = datetime.now()
            if completed_at is None:
                completed_at = datetime.now()

            # detailsをJSON文字列に変換
            details_json = None
            if details:
                import json

                details_json = json.dumps(details, ensure_ascii=False, default=str)

            cursor.execute(
                """
                INSERT INTO execution_logs
                (execution_type, instagram_id, account_id, location_id, status, message, details,
                 posts_count, stories_count, success_count, failed_count, skipped_count,
                 error_message, execution_time_seconds, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    execution_type,
                    instagram_id,
                    account_id,
                    location_id,
                    status,
                    message,
                    details_json,
                    posts_count,
                    stories_count,
                    success_count,
                    failed_count,
                    skipped_count,
                    error_message,
                    execution_time_seconds,
                    started_at,
                    completed_at,
                ),
            )

            log_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.debug(f"実行ログを記録: {execution_type} - {status} (ID: {log_id})")
            return log_id

        except Exception as e:
            logger.error(f"実行ログ記録エラー: {e}")
            return -1

    def get_execution_logs(
        self,
        execution_type: str | None = None,
        instagram_id: str | None = None,
        account_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        実行ログを取得

        Args:
            execution_type: 実行タイプでフィルタ
            instagram_id: Instagram IDでフィルタ
            account_id: Google Business Profile アカウントIDでフィルタ
            location_id: Google Business Profile ロケーションIDでフィルタ
            status: ステータスでフィルタ
            limit: 取得件数
            offset: オフセット

        Returns:
            実行ログのリスト
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            conditions = []
            params = []

            if execution_type:
                conditions.append("execution_type = ?")
                params.append(execution_type)

            if instagram_id:
                conditions.append("instagram_id = ?")
                params.append(instagram_id)

            if account_id:
                conditions.append("account_id = ?")
                params.append(account_id)

            if location_id:
                conditions.append("location_id = ?")
                params.append(location_id)

            if status:
                conditions.append("status = ?")
                params.append(status)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT * FROM execution_logs
                {where_clause}
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            cursor.execute(query, params)

            rows = cursor.fetchall()
            conn.close()

            # detailsをJSONから辞書に変換
            logs = []
            for row in rows:
                log_dict = dict(row)
                if log_dict.get("details"):
                    try:
                        import json

                        log_dict["details"] = json.loads(log_dict["details"])
                    except:
                        pass
                logs.append(log_dict)

            return logs

        except Exception as e:
            logger.error(f"実行ログ取得エラー: {e}")
            return []

    def get_execution_summary(
        self,
        instagram_id: str | None = None,
        account_id: str | None = None,
        location_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        実行ログのサマリーを取得

        Args:
            instagram_id: Instagram IDでフィルタ
            account_id: Google Business Profile アカウントIDでフィルタ
            location_id: Google Business Profile ロケーションIDでフィルタ
            days: 過去何日分のログを集計するか

        Returns:
            サマリー情報の辞書
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            conditions = ["started_at >= datetime('now', '-' || ? || ' days')"]
            params = [days]

            if instagram_id:
                conditions.append("instagram_id = ?")
                params.append(instagram_id)

            if account_id:
                conditions.append("account_id = ?")
                params.append(account_id)

            if location_id:
                conditions.append("location_id = ?")
                params.append(location_id)

            where_clause = "WHERE " + " AND ".join(conditions)

            # 総実行回数
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM execution_logs {where_clause}
            """,
                params,
            )
            total_executions = cursor.fetchone()[0]

            # ステータス別の集計
            cursor.execute(
                f"""
                SELECT status, COUNT(*) as count
                FROM execution_logs {where_clause}
                GROUP BY status
            """,
                params,
            )
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 実行タイプ別の集計
            cursor.execute(
                f"""
                SELECT execution_type, COUNT(*) as count
                FROM execution_logs {where_clause}
                GROUP BY execution_type
            """,
                params,
            )
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 総処理件数
            cursor.execute(
                f"""
                SELECT 
                    SUM(posts_count) as total_posts,
                    SUM(stories_count) as total_stories,
                    SUM(success_count) as total_success,
                    SUM(failed_count) as total_failed,
                    SUM(skipped_count) as total_skipped
                FROM execution_logs {where_clause}
            """,
                params,
            )
            row = cursor.fetchone()
            total_counts = {
                "posts": row[0] or 0,
                "stories": row[1] or 0,
                "success": row[2] or 0,
                "failed": row[3] or 0,
                "skipped": row[4] or 0,
            }

            # 平均実行時間
            cursor.execute(
                f"""
                SELECT AVG(execution_time_seconds) as avg_time
                FROM execution_logs
                {where_clause} AND execution_time_seconds IS NOT NULL
            """,
                params,
            )
            avg_time = cursor.fetchone()[0] or 0

            conn.close()

            return {
                "total_executions": total_executions,
                "status_counts": status_counts,
                "type_counts": type_counts,
                "total_counts": total_counts,
                "average_execution_time_seconds": round(avg_time, 2),
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"実行ログサマリー取得エラー: {e}")
            return {}
