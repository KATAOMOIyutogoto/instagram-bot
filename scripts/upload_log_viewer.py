"""
アップロードログビューアー
モックアップロード時に記録されたログデータを表示
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class UploadLogViewer:
    """アップロードログを表示・取得するクラス"""

    def __init__(self, log_file: str = "data/upload_mock_logs.json"):
        """
        Args:
            log_file: ログファイルのパス（JSON形式）
        """
        self.log_file = Path(log_file)
        self._ensure_log_file()

    def _ensure_log_file(self):
        """ログファイルが存在しない場合は作成"""
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def add_upload_log(
        self,
        upload_type: str,
        taken_at: datetime,
        instagram_id: str,
        account_id: str,
        location_id: str,
        uploaded_urls: list[str],
        caption: str = "",
        post_id: str | None = None,
        story_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        target_files: list[str] | None = None,
        skipped: bool = False,
        upload_status: str = "uploaded",
    ):
        """
        アップロードログを追加

        Args:
            upload_type: アップロードタイプ ('post' または 'story')
            taken_at: 投稿/ストーリーの日時
            instagram_id: Instagram ID
            account_id: Google Business Profile アカウントID
            location_id: Google Business Profile ロケーションID
            uploaded_urls: アップロードしたファイルのURLリスト
            caption: キャプション（投稿の場合のみ）
            post_id: 投稿ID（投稿の場合）
            story_id: ストーリーID（ストーリーの場合）
            metadata: メタデータ（オプション）
            target_files: アップロード対象のファイルパスリスト（元のファイルパス）
            skipped: スキップされたかどうか（重複チェックでスキップされた場合True）
            upload_status: アップロード状態 ('uploaded', 'skipped', 'failed')
        """
        try:
            # 既存のログを読み込む
            logs = self.get_all_logs()

            # 実行日時を取得
            execution_date = datetime.now()

            # 新しいログエントリを作成
            log_entry = {
                "execution_date": execution_date.isoformat(),  # 実行日時
                "upload_type": upload_type,
                "taken_at": (
                    taken_at.isoformat() if isinstance(taken_at, datetime) else str(taken_at)
                ),
                "instagram_id": instagram_id,
                "account_id": account_id,
                "location_id": location_id,
                "target_files": target_files or [],  # アップロード対象のファイルパス
                "uploaded_urls": uploaded_urls,  # アップロードしたファイルのURL（モックではfile://形式）
                "skipped": skipped,  # スキップされたかどうか
                "upload_status": upload_status,  # アップロード状態
                "caption": caption,
                "post_id": post_id,
                "story_id": story_id,
                "upload_date": execution_date.isoformat(),  # 後方互換性のため残す
                "metadata": metadata or {},
            }

            logs.append(log_entry)

            # ログを保存（最新1000件まで保持）
            logs = logs[-1000:]

            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)

            logger.debug(f"アップロードログを追加: {upload_type} - {taken_at}")

        except Exception as e:
            logger.error(f"アップロードログ追加エラー: {e}")

    def get_all_logs(
        self,
        instagram_id: str | None = None,
        account_id: str | None = None,
        location_id: str | None = None,
        upload_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        すべてのアップロードログを取得

        Args:
            instagram_id: Instagram IDでフィルタ
            account_id: Google Business Profile アカウントIDでフィルタ
            location_id: Google Business Profile ロケーションIDでフィルタ
            upload_type: アップロードタイプでフィルタ ('post' または 'story')

        Returns:
            ログエントリのリスト
        """
        try:
            if not self.log_file.exists():
                return []

            with open(self.log_file, encoding="utf-8") as f:
                logs = json.load(f)

            # フィルタリング
            filtered_logs = []
            for log in logs:
                if instagram_id and log.get("instagram_id") != instagram_id:
                    continue
                # 後方互換性: store_id もチェック（古いログ用）
                if account_id:
                    if log.get("account_id") != account_id and log.get("store_id") != account_id:
                        continue
                if location_id:
                    if log.get("location_id") != location_id and log.get("store_id") != location_id:
                        continue
                if upload_type and log.get("upload_type") != upload_type:
                    continue
                filtered_logs.append(log)

            # 日時でソート（新しい順）
            filtered_logs.sort(key=lambda x: x.get("upload_date", ""), reverse=True)

            return filtered_logs

        except Exception as e:
            logger.error(f"アップロードログ取得エラー: {e}")
            return []

    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        最近のアップロードログを取得

        Args:
            limit: 取得件数

        Returns:
            ログエントリのリスト
        """
        logs = self.get_all_logs()
        return logs[:limit]

    def format_log_for_client(self, log: dict[str, Any]) -> dict[str, Any]:
        """
        クライアントに提示するための形式にログを整形

        Args:
            log: ログデータ

        Returns:
            整形されたログデータ
        """
        upload_type_jp = {"post": "投稿", "story": "ストーリー"}.get(
            log.get("upload_type"), log.get("upload_type")
        )

        # 後方互換性: store_id がある場合は account_id/location_id として扱う
        account_id = log.get("account_id") or log.get("store_id", "")
        location_id = log.get("location_id") or log.get("store_id", "")

        formatted = {
            "アップロード日時": log.get("upload_date"),
            "投稿/ストーリー日時": log.get("taken_at"),
            "タイプ": upload_type_jp,
            "Instagram ID": log.get("instagram_id"),
            "アカウントID": account_id,
            "ロケーションID": location_id,
            "アップロードURL": log.get("uploaded_urls", []),
            "キャプション": log.get("caption", ""),
            "投稿ID": log.get("post_id"),
            "ストーリーID": log.get("story_id"),
        }

        return formatted

    def print_client_report(
        self,
        instagram_id: str | None = None,
        account_id: str | None = None,
        location_id: str | None = None,
        upload_type: str | None = None,
        limit: int = 50,
    ):
        """
        クライアントに提示するためのレポートを表示

        Args:
            instagram_id: Instagram IDでフィルタ
            account_id: Google Business Profile アカウントIDでフィルタ
            location_id: Google Business Profile ロケーションIDでフィルタ
            upload_type: アップロードタイプでフィルタ
            limit: 表示件数
        """
        logs = self.get_all_logs(
            instagram_id=instagram_id,
            account_id=account_id,
            location_id=location_id,
            upload_type=upload_type,
        )[:limit]

        if not logs:
            print("\nアップロードログがありません。")
            return

        print("\n" + "=" * 80)
        print("アップロードログレポート")
        print("=" * 80)

        for i, log in enumerate(logs, 1):
            formatted = self.format_log_for_client(log)

            print(f"\n[{i}] 実行日時: {formatted['実行日時']}")
            print(f"    タイプ: {formatted['タイプ']}")
            print(f"    投稿/ストーリー日時: {formatted['投稿/ストーリー日時']}")
            print(f"    Instagram ID: {formatted['Instagram ID']}")
            print(f"    アカウントID: {formatted['アカウントID']}")
            print(f"    ロケーションID: {formatted['ロケーションID']}")
            print(f"    アップロード状態: {formatted['アップロード状態']}")
            print(f"    スキップ: {formatted['スキップ']}")

            if formatted.get("投稿ID"):
                print(f"    投稿ID: {formatted['投稿ID']}")
            if formatted.get("ストーリーID"):
                print(f"    ストーリーID: {formatted['ストーリーID']}")

            if formatted.get("アップロード対象ファイル"):
                print("    アップロード対象ファイル:")
                for file_path in formatted["アップロード対象ファイル"]:
                    print(f"      - {file_path}")

            if formatted.get("アップロードURL"):
                print("    アップロードURL:")
                for url in formatted["アップロードURL"]:
                    print(f"      - {url}")

            if formatted.get("キャプション"):
                caption = formatted["キャプション"]
                print("    キャプション:")
                # キャプションを複数行で表示（最大500文字）
                caption_preview = caption[:500] + ("..." if len(caption) > 500 else "")
                for line in caption_preview.split("\n"):
                    print(f"      {line}")

        print("\n" + "=" * 80)
        print(f"合計: {len(logs)}件")
