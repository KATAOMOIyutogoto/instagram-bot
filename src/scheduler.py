"""
スケジューラーモジュール
1時間ごとに全アカウントを処理する
"""

import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Unix/Linux用のfcntl（Windowsでは使用不可）
try:
    import fcntl
except ImportError:
    fcntl = None  # WindowsではNone

logger = logging.getLogger(__name__)


class LockFile:
    """ロックファイル管理クラス（前の処理が完了しているかチェック）"""

    def __init__(self, lock_file_path: str = "data/scheduler.lock"):
        """
        Args:
            lock_file_path: ロックファイルのパス
        """
        self.lock_file_path = Path(lock_file_path)
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file = None
        self.is_locked = False

    def acquire(self, timeout: float = 0) -> bool:
        """
        ロックを取得（前の処理が実行中でないかチェック）

        Args:
            timeout: ロック取得のタイムアウト（秒）。0の場合は即座に返る

        Returns:
            ロック取得成功したかどうか
        """
        if self.is_locked:
            return True

        try:
            # Windows用のロック処理
            if sys.platform == "win32":
                # Windowsではファイルの排他アクセスでロック
                try:
                    self.lock_file = open(self.lock_file_path, "w")
                    # ファイルを排他モードで開く（他のプロセスが開けない）
                    # Windowsでは、ファイルの存在チェックとPIDチェックでロックを実現
                    if self.lock_file_path.exists():
                        # ロックファイルが存在する場合、PIDを確認
                        try:
                            with open(self.lock_file_path) as f:
                                pid_str = f.read().strip()
                                if pid_str:
                                    pid = int(pid_str)
                                    # プロセスが存在するかチェック
                                    try:
                                        import psutil

                                        if psutil.pid_exists(pid):
                                            logger.warning(f"前の処理が実行中です (PID: {pid})")
                                            self.lock_file.close()
                                            self.lock_file = None
                                            return False
                                    except ImportError:
                                        # psutilが使えない場合は、プロセスの存在確認をスキップ
                                        logger.warning(
                                            "psutilがインストールされていません。ロックチェックをスキップします。"
                                        )
                                        # 既存のロックファイルを削除して続行
                                        self.lock_file_path.unlink()
                        except (ValueError, FileNotFoundError, OSError):
                            # ロックファイルが読み取れない場合は削除して続行
                            try:
                                self.lock_file_path.unlink()
                            except:
                                pass

                    # PIDを書き込む
                    import os

                    self.lock_file.write(str(os.getpid()))
                    self.lock_file.flush()

                    self.is_locked = True
                    logger.info(f"ロックを取得しました: {self.lock_file_path}")
                    return True
                except OSError as e:
                    logger.warning(
                        f"ロック取得に失敗しました（前の処理が実行中かもしれません）: {e}"
                    )
                    if self.lock_file:
                        self.lock_file.close()
                        self.lock_file = None
                    return False
            else:
                # Unix/Linux用のロック処理
                if fcntl is None:
                    logger.error("fcntlモジュールが利用できません（Windowsでは使用できません）")
                    return False

                self.lock_file = open(self.lock_file_path, "w")
                try:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # PIDを書き込む
                    import os

                    self.lock_file.write(str(os.getpid()))
                    self.lock_file.flush()
                    self.is_locked = True
                    logger.info(f"ロックを取得しました: {self.lock_file_path}")
                    return True
                except OSError:
                    logger.warning("ロック取得に失敗しました（前の処理が実行中かもしれません）")
                    self.lock_file.close()
                    self.lock_file = None
                    return False
        except Exception as e:
            logger.error(f"ロック取得エラー: {e}")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False

    def release(self):
        """ロックを解放"""
        if not self.is_locked:
            return

        try:
            if self.lock_file:
                if sys.platform != "win32":
                    # Unix/Linuxのみfcntlを使用
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)

                self.lock_file.close()
                self.lock_file = None

            # ロックファイルを削除
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()

            self.is_locked = False
            logger.info("ロックを解放しました")
        except Exception as e:
            logger.error(f"ロック解放エラー: {e}")

    def __enter__(self):
        """コンテキストマネージャー: ロック取得"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー: ロック解放"""
        self.release()


class Scheduler:
    """定期実行スケジューラー"""

    def __init__(self, interval_hours: float = 1.0, lock_file_path: str = "data/scheduler.lock"):
        """
        Args:
            interval_hours: 実行間隔（時間）
            lock_file_path: ロックファイルのパス
        """
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.lock_file = LockFile(lock_file_path)
        self.running = False
        self.thread: threading.Thread | None = None

    def run_once(self) -> bool:
        """
        1回だけ実行（ロックチェック付き）

        Returns:
            実行成功したかどうか（ロック取得失敗の場合はFalse）
        """
        # ロックを取得
        if not self.lock_file.acquire():
            logger.warning("前の処理が完了していないため、スキップします")
            return False

        try:
            logger.info("=" * 60)
            logger.info(f"定期実行を開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            # メイン処理を実行
            import sys
            from pathlib import Path

            # プロジェクトルートをパスに追加
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from src.main import InstagramDownloadBot

            bot = InstagramDownloadBot("config/config.json")

            # 企業リストファイルが指定されている場合は読み込む
            companies_file = Path("companies.txt")
            if companies_file.exists():
                bot.load_companies_from_file(str(companies_file))

            # 7アカウント対応後は、download_all_companies()内で各アカウントを個別に初期化するため、
            # 最初の初期化は不要（複数アカウントが設定されている場合はスキップ）
            if not bot.instagram_accounts or len(bot.instagram_accounts) == 1:
                # 単一アカウントの場合のみ初期化
                if not bot.initialize():
                    logger.error("Botの初期化に失敗しました")
                    return False

            # すべての企業のコンテンツをダウンロード
            results = bot.download_all_companies()

            # 結果サマリーを表示
            logger.info("\n=== ダウンロード結果サマリー ===")
            for company, result in results.items():
                if "error" in result:
                    logger.error(f"{company}: エラー - {result['error']}")
                else:
                    posts_count = len(result.get("posts", []))
                    stories_count = len(result.get("stories", []))
                    upload_info = ""
                    if result.get("upload"):
                        upload_posts = result["upload"].get("posts", {})
                        upload_stories = result["upload"].get("stories", {})
                        if upload_posts or upload_stories:
                            upload_info = f" (アップロード: 投稿{upload_posts.get('success', 0)}件, ストーリー{upload_stories.get('success', 0)}件)"
                    logger.info(
                        f"{company}: 投稿 {posts_count}件, ストーリー {stories_count}件{upload_info}"
                    )

            logger.info("=" * 60)
            logger.info(f"定期実行が完了しました: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"定期実行エラー: {e}", exc_info=True)
            return False

        finally:
            # ロックを解放
            self.lock_file.release()

    def start(self):
        """スケジューラーを開始（バックグラウンドで定期実行）"""
        if self.running:
            logger.warning("スケジューラーは既に実行中です")
            return

        self.running = True

        def scheduler_loop():
            logger.info(f"スケジューラーを開始しました（間隔: {self.interval_hours}時間）")

            while self.running:
                try:
                    # 1回実行
                    self.run_once()

                    # 次の実行まで待機
                    if self.running:
                        logger.info(f"次の実行まで {self.interval_hours}時間待機します...")
                        # 待機中に停止フラグをチェック
                        wait_interval = 60  # 1分ごとにチェック
                        waited = 0
                        while self.running and waited < self.interval_seconds:
                            time.sleep(wait_interval)
                            waited += wait_interval

                except KeyboardInterrupt:
                    logger.info("スケジューラーが中断されました")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"スケジューラーエラー: {e}", exc_info=True)
                    # エラーが発生しても続行（次の実行まで待機）
                    if self.running:
                        time.sleep(60)  # 1分待機してから再試行

        self.thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """スケジューラーを停止"""
        logger.info("スケジューラーを停止しています...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        self.lock_file.release()
        logger.info("スケジューラーを停止しました")


def main():
    """スケジューラーのメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Bot スケジューラー")
    parser.add_argument(
        "--interval", type=float, default=1.0, help="実行間隔（時間）。デフォルト: 1.0時間"
    )
    parser.add_argument("--once", action="store_true", help="1回だけ実行して終了（定期実行しない）")
    parser.add_argument(
        "--lock-file", type=str, default="data/scheduler.lock", help="ロックファイルのパス"
    )

    args = parser.parse_args()

    # ログ設定
    # コンソール出力用のUTF-8エンコーディングハンドラー
    class UTF8StreamHandler(logging.StreamHandler):
        """UTF-8エンコーディングでコンソールに出力するハンドラー"""
        
        def __init__(self, stream=None):
            super().__init__(stream)
            # Windowsの場合、標準出力のエンコーディングをUTF-8に設定
            if sys.platform == "win32":
                if hasattr(sys.stdout, "reconfigure"):
                    try:
                        sys.stdout.reconfigure(encoding="utf-8")
                    except Exception:
                        pass
                if hasattr(sys.stderr, "reconfigure"):
                    try:
                        sys.stderr.reconfigure(encoding="utf-8")
                    except Exception:
                        pass
        
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                # UTF-8でエンコードして出力（バッファがある場合）
                if hasattr(stream, "buffer"):
                    stream.buffer.write(msg.encode("utf-8"))
                    stream.buffer.write(b"\n")
                    self.flush()
                else:
                    # バッファがない場合は通常の方法で出力
                    stream.write(msg)
                    stream.write("\n")
                    self.flush()
            except Exception:
                self.handleError(record)
    
    # logsディレクトリが存在しない場合は作成
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/scheduler.log", encoding="utf-8"),
            UTF8StreamHandler(),
        ],
    )

    scheduler = Scheduler(interval_hours=args.interval, lock_file_path=args.lock_file)

    if args.once:
        # 1回だけ実行
        success = scheduler.run_once()
        sys.exit(0 if success else 1)
    else:
        # 定期実行
        try:
            scheduler.start()
            # メインスレッドをブロック（Ctrl+Cで停止）
            while scheduler.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("スケジューラーを停止します...")
            scheduler.stop()
            sys.exit(0)


if __name__ == "__main__":
    main()
