"""
実行ログビューアー
クライアントに提示するためのログ表示機能
"""

import logging
from typing import Any

from src.database import UploadDatabase

logger = logging.getLogger(__name__)


class LogViewer:
    """実行ログを表示・取得するクラス"""

    def __init__(self, db_path: str = "data/upload_history.db"):
        """
        Args:
            db_path: データベースファイルのパス
        """
        self.db = UploadDatabase(db_path)

    def get_recent_logs(
        self,
        limit: int = 50,
        execution_type: str | None = None,
        instagram_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        最近の実行ログを取得

        Args:
            limit: 取得件数
            execution_type: 実行タイプでフィルタ
            instagram_id: Instagram IDでフィルタ
            status: ステータスでフィルタ

        Returns:
            実行ログのリスト
        """
        return self.db.get_execution_logs(
            execution_type=execution_type, instagram_id=instagram_id, status=status, limit=limit
        )

    def get_log_summary(self, instagram_id: str | None = None, days: int = 30) -> dict[str, Any]:
        """
        実行ログのサマリーを取得

        Args:
            instagram_id: Instagram IDでフィルタ
            days: 過去何日分のログを集計するか

        Returns:
            サマリー情報の辞書
        """
        return self.db.get_execution_summary(instagram_id=instagram_id, days=days)

    def format_log_for_client(self, log: dict[str, Any]) -> dict[str, Any]:
        """
        クライアントに提示するための形式にログを整形

        Args:
            log: ログデータ

        Returns:
            整形されたログデータ
        """
        # ステータスを日本語に変換
        status_map = {"success": "成功", "failed": "失敗", "partial_success": "一部成功"}

        # 実行タイプを日本語に変換
        type_map = {
            "download": "ダウンロード",
            "upload": "アップロード",
            "download_and_upload": "ダウンロード＆アップロード",
        }

        formatted = {
            "id": log.get("id"),
            "実行日時": log.get("started_at"),
            "実行タイプ": type_map.get(log.get("execution_type"), log.get("execution_type")),
            "ステータス": status_map.get(log.get("status"), log.get("status")),
            "メッセージ": log.get("message", ""),
            "Instagram ID": log.get("instagram_id"),
            "アカウントID": log.get("account_id"),
            "ロケーションID": log.get("location_id"),
            "投稿数": log.get("posts_count", 0),
            "ストーリー数": log.get("stories_count", 0),
            "成功件数": log.get("success_count", 0),
            "失敗件数": log.get("failed_count", 0),
            "スキップ件数": log.get("skipped_count", 0),
            "実行時間": (
                f"{log.get('execution_time_seconds', 0):.2f}秒"
                if log.get("execution_time_seconds")
                else None
            ),
            "エラーメッセージ": log.get("error_message"),
            "詳細": log.get("details", {}),
        }

        return formatted

    def get_client_report(
        self, instagram_id: str | None = None, days: int = 30, limit: int = 50
    ) -> dict[str, Any]:
        """
        クライアントに提示するためのレポートを生成

        Args:
            instagram_id: Instagram IDでフィルタ
            days: 過去何日分のログを集計するか
            limit: 取得するログ件数

        Returns:
            レポートデータ
        """
        # サマリーを取得
        summary = self.get_log_summary(instagram_id=instagram_id, days=days)

        # 最近のログを取得
        recent_logs = self.get_recent_logs(limit=limit, instagram_id=instagram_id)

        # ログを整形
        formatted_logs = [self.format_log_for_client(log) for log in recent_logs]

        # レポートを生成
        report = {
            "期間": f"過去{days}日間",
            "サマリー": {
                "総実行回数": summary.get("total_executions", 0),
                "ステータス別": summary.get("status_counts", {}),
                "実行タイプ別": summary.get("type_counts", {}),
                "総処理件数": {
                    "投稿": summary.get("total_counts", {}).get("posts", 0),
                    "ストーリー": summary.get("total_counts", {}).get("stories", 0),
                    "成功": summary.get("total_counts", {}).get("success", 0),
                    "失敗": summary.get("total_counts", {}).get("failed", 0),
                    "スキップ": summary.get("total_counts", {}).get("skipped", 0),
                },
                "平均実行時間": f"{summary.get('average_execution_time_seconds', 0):.2f}秒",
            },
            "最近の実行履歴": formatted_logs,
        }

        return report

    def print_client_report(self, instagram_id: str | None = None, days: int = 30, limit: int = 50):
        """
        クライアントに提示するためのレポートを表示

        Args:
            instagram_id: Instagram IDでフィルタ
            days: 過去何日分のログを集計するか
            limit: 取得するログ件数
        """
        report = self.get_client_report(instagram_id=instagram_id, days=days, limit=limit)

        print("\n" + "=" * 60)
        print("実行ログレポート")
        print("=" * 60)
        print(f"\n期間: {report['期間']}")

        print("\n【サマリー】")
        summary = report["サマリー"]
        print(f"  総実行回数: {summary['総実行回数']}回")
        print(f"  平均実行時間: {summary['平均実行時間']}")

        print("\n  ステータス別:")
        for status, count in summary["ステータス別"].items():
            status_jp = {"success": "成功", "failed": "失敗", "partial_success": "一部成功"}.get(
                status, status
            )
            print(f"    {status_jp}: {count}回")

        print("\n  実行タイプ別:")
        for exec_type, count in summary["実行タイプ別"].items():
            type_jp = {
                "download": "ダウンロード",
                "upload": "アップロード",
                "download_and_upload": "ダウンロード＆アップロード",
            }.get(exec_type, exec_type)
            print(f"    {type_jp}: {count}回")

        print("\n  総処理件数:")
        counts = summary["総処理件数"]
        print(f"    投稿: {counts['投稿']}件")
        print(f"    ストーリー: {counts['ストーリー']}件")
        print(f"    成功: {counts['成功']}件")
        print(f"    失敗: {counts['失敗']}件")
        print(f"    スキップ: {counts['スキップ']}件")

        print("\n【最近の実行履歴】")
        for i, log in enumerate(report["最近の実行履歴"][:10], 1):
            print(f"\n  [{i}] {log['実行日時']}")
            print(f"      タイプ: {log['実行タイプ']}")
            print(f"      ステータス: {log['ステータス']}")
            print(f"      メッセージ: {log['メッセージ']}")
            if log.get("Instagram ID"):
                print(f"      Instagram ID: {log['Instagram ID']}")
            if log.get("アカウントID"):
                print(f"      アカウントID: {log['アカウントID']}")
            if log.get("ロケーションID"):
                print(f"      ロケーションID: {log['ロケーションID']}")
            if log.get("実行時間"):
                print(f"      実行時間: {log['実行時間']}")
            if log.get("エラーメッセージ"):
                print(f"      エラー: {log['エラーメッセージ']}")

        print("\n" + "=" * 60)
