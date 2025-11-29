"""
ユーティリティ関数
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# HTMLレスポンスをフィルタリングするカスタムフィルター
class HTMLFilter(logging.Filter):
    """HTMLコンテンツを含むログメッセージを抑制または短縮するフィルター"""

    def filter(self, record):
        """ログレコードをフィルタリング"""
        # メッセージがHTMLを含む場合、短縮または抑制
        msg_str = str(record.msg) if hasattr(record, "msg") else ""

        # メッセージがHTMLを含む場合
        if "<!DOCTYPE" in msg_str or "<html" in msg_str.lower() or "<script" in msg_str.lower():
            # HTMLを含むログは完全に抑制
            return False

        # argsにHTMLが含まれる場合も処理
        if hasattr(record, "args") and record.args:
            for arg in record.args:
                if isinstance(arg, str):
                    if "<!DOCTYPE" in arg or "<html" in arg.lower() or "<script" in arg.lower():
                        # HTMLを含むログは完全に抑制
                        return False

        return True


# ログ設定
# ログディレクトリが存在しない場合は作成
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

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
        logging.FileHandler("logs/instagram_bot.log", encoding="utf-8"),
        UTF8StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# instagrapiライブラリのログレベルをCRITICALに設定（HTMLレスポンスの大量出力を防ぐ）
logging.getLogger("instagrapi").setLevel(logging.CRITICAL)
logging.getLogger("private_request").setLevel(logging.CRITICAL)
logging.getLogger("public_request").setLevel(logging.CRITICAL)
logging.getLogger("instagrapi.mixins").setLevel(logging.CRITICAL)

# すべてのハンドラーにHTMLフィルターを追加
html_filter = HTMLFilter()
for handler in logging.root.handlers:
    handler.addFilter(html_filter)


def load_config(config_path: str = "config/config.json") -> dict[str, Any]:
    """設定ファイルを読み込む"""
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        logger.info(f"設定ファイルを読み込みました: {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"設定ファイルのJSON解析エラー: {e}")
        raise


def save_config(config: dict[str, Any], config_path: str = "config/config.json") -> None:
    """設定ファイルを保存する"""
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"設定ファイルを保存しました: {config_path}")
    except Exception as e:
        logger.error(f"設定ファイルの保存エラー: {e}")
        raise


def get_download_path(
    base_dir: str,
    company: str,
    media_type: str,
    organize_by_company: bool = True,
    organize_by_date: bool = True,
    taken_at: datetime | None = None,
) -> Path:
    """
    ダウンロード先のパスを生成

    Args:
        base_dir: ベースディレクトリ
        company: 企業名（ユーザー名）
        media_type: メディアタイプ（posts/stories）
        organize_by_company: 企業ごとにフォルダ分けするか
        organize_by_date: 日付ごとにフォルダ分けするか
        taken_at: メディアのアップロード日時（指定された場合はこれを使用）

    Returns:
        ダウンロード先のPathオブジェクト
    """
    path = Path(base_dir)

    if organize_by_company:
        path = path / company

    if organize_by_date:
        if taken_at:
            # アップロード日時を使用（重複を避けるため日時まで含める）
            date_str = taken_at.strftime("%Y-%m-%d_%H-%M")
        else:
            # フォールバック: 現在の日時を使用
            date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        path = path / date_str

    path = path / media_type
    path.mkdir(parents=True, exist_ok=True)

    return path


def load_companies_from_file(file_path: str) -> list[str]:
    """ファイルから企業リストを読み込む（1行1企業、#で始まる行はコメント）"""
    try:
        with open(file_path, encoding="utf-8") as f:
            companies = [
                line.strip() for line in f if line.strip() and not line.strip().startswith("#")
            ]
        logger.info(f"{len(companies)}社の企業リストを読み込みました: {file_path}")
        return companies
    except FileNotFoundError:
        logger.warning(f"企業リストファイルが見つかりません: {file_path}")
        return []


def save_companies_to_file(companies: list[str], file_path: str) -> None:
    """企業リストをファイルに保存する"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for company in companies:
                f.write(f"{company}\n")
        logger.info(f"企業リストを保存しました: {file_path}")
    except Exception as e:
        logger.error(f"企業リストの保存エラー: {e}")
        raise


def validate_config(config: dict[str, Any]) -> bool:
    """設定ファイルの妥当性をチェック"""
    required_keys = ["instagram", "targets", "download", "settings"]

    for key in required_keys:
        if key not in config:
            logger.error(f"設定ファイルに必須キー '{key}' がありません")
            return False

    if not config["instagram"].get("username") or not config["instagram"].get("password"):
        logger.warning("Instagramのユーザー名またはパスワードが設定されていません")

    if not config["targets"].get("companies"):
        logger.warning("ターゲット企業が設定されていません")

    return True
