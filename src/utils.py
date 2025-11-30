"""
ユーティリティ関数
"""

import json
import logging
import os
import subprocess
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


def ensure_video_resolution(
    file_path: str,
    min_width: int = 400,
    min_height: int = 300,
) -> str:
    """
    動画の解像度をチェックし、必要に応じて変換
    
    Google Business Profileの要件:
    - 最小解像度: 400x300ピクセル
    - 幅・高さは偶数である必要がある（H.264エンコーディングの要件）
    
    Args:
        file_path: 動画ファイルのパス
        min_width: 最小幅（デフォルト: 400）
        min_height: 最小高さ（デフォルト: 300）
    
    Returns:
        変換後のファイルパス（変換不要の場合は元のパス）
    """
    try:
        # OpenCVが利用可能かチェック
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCVがインストールされていません。動画の解像度チェックをスキップします。")
            return file_path
        
        # 動画サイズを取得
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            logger.warning(f"動画ファイルを開けませんでした: {file_path}")
            return file_path
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        logger.info(f"元の動画サイズ: {width}x{height}")

        # 幅と高さが最小サイズ以上、かつ偶数なら変換不要
        if width >= min_width and height >= min_height and width % 2 == 0 and height % 2 == 0:
            logger.info("動画のサイズは要件を満たしており変換不要です")
            return file_path

        logger.info("動画のサイズが要件を満たしていないため変換を実施します")

        # FFmpegが利用可能かチェック
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpegが見つかりません。動画の変換をスキップします。")
            logger.warning("FFmpegをインストールしてから再実行してください。")
            return file_path

        # 変換後のファイル名
        base, ext = os.path.splitext(file_path)
        resized_file = f"{base}_resized{ext}"

        # FFmpegで変換（Googleの最低要件 + H.264の偶数制限）
        command = [
            "ffmpeg",
            "-i", file_path,
            "-vf", "scale='if(lt(iw,400),trunc(400/2)*2,trunc(iw/2)*2)':'if(lt(ih,300),trunc(300/2)*2,trunc(ih/2)*2)'",
            "-c:a", "copy",
            "-y",  # 上書き確認をスキップ
            resized_file
        ]

        logger.info(f"ffmpegコマンド: {' '.join(command)}")

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            logger.error("ffmpeg stderr:\n" + result.stderr)
            logger.warning("動画変換に失敗しました。元のファイルを使用します。")
            return file_path

        logger.info(f"変換完了: {resized_file}")

        # 元ファイルを削除
        try:
            os.remove(file_path)
            logger.info(f"元ファイルを削除しました: {file_path}")
        except Exception as delete_error:
            logger.warning(f"元ファイルの削除に失敗しました: {delete_error}")

        return resized_file

    except Exception as e:
        logger.error(f"動画の変換に失敗しました: {e}")
        return file_path


def optimize_image_size(
    file_path: str,
    max_size_mb: float = 5.0,
    max_dimension: int = 2048,
    quality: int = 85,
    min_size_kb: float = 10.0,
) -> str:
    """
    画像ファイルのサイズを最適化（圧縮・リサイズ）
    
    Google Business Profileのアップロード時のファイルサイズ制限に対応するため、
    画像ファイルが大きすぎる場合に圧縮・リサイズを実行します。
    また、10KB未満の画像は10KB以上になるように調整します。
    
    Args:
        file_path: 画像ファイルのパス
        max_size_mb: 最大ファイルサイズ（MB、デフォルト: 5.0MB）
        max_dimension: 最大幅・高さ（ピクセル、デフォルト: 2048）
        quality: JPEG品質（1-100、デフォルト: 85）
        min_size_kb: 最小ファイルサイズ（KB、デフォルト: 10.0KB）
    
    Returns:
        最適化後のファイルパス（最適化不要の場合は元のパス）
    """
    try:
        # Pillowが利用可能かチェック
        try:
            from PIL import Image, ImageOps
        except ImportError:
            logger.warning("Pillowがインストールされていません。画像の最適化をスキップします。")
            return file_path
        
        # ファイルサイズをチェック
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        file_size_kb = file_size_bytes / 1024
        logger.info(f"元の画像ファイルサイズ: {file_size_kb:.2f}KB ({file_size_mb:.2f}MB)")
        
        # 画像ファイルかどうかチェック
        path = Path(file_path)
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if path.suffix.lower() not in image_extensions:
            logger.debug(f"画像ファイルではないためスキップ: {file_path}")
            return file_path
        
        # 画像を開く
        try:
            with Image.open(file_path) as original_img:
                # EXIF情報を保持（回転情報など）
                try:
                    img = ImageOps.exif_transpose(original_img.copy())
                except Exception:
                    img = original_img.copy()
                
                original_width, original_height = img.size
                logger.info(f"元の画像サイズ: {original_width}x{original_height}")
                
                # 最適化後のファイル名
                base, ext = os.path.splitext(file_path)
                output_ext = ".jpg" if ext.lower() in [".png", ".gif", ".webp"] else ext.lower()
                optimized_file = f"{base}_optimized{output_ext}"
                
                # RGBモードに変換（PNGの透過などは削除）
                if img.mode in ("RGBA", "P"):
                    # 透過を白背景で処理
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        background.paste(img, mask=img.split()[-1])  # アルファチャンネルをマスクとして使用
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                
                # 最小サイズチェック（10KB未満の場合は調整）
                if file_size_kb < min_size_kb:
                    logger.warning(f"画像ファイルが{min_size_kb}KB未満です（{file_size_kb:.2f}KB）。{min_size_kb}KB以上になるように調整します")
                    
                    # 品質を上げて10KB以上になるようにする
                    current_quality = min(quality + 20, 100)  # 品質を上げる（最大100）
                    img.save(optimized_file, "JPEG", quality=current_quality, optimize=True)
                    optimized_size_kb = os.path.getsize(optimized_file) / 1024
                    
                    # まだ10KB未満の場合は、解像度を上げる
                    if optimized_size_kb < min_size_kb:
                        logger.info(f"品質を上げても{min_size_kb}KB未満のため、解像度を上げます")
                        scale_factor = 1.2  # 20%拡大
                        new_width = int(original_width * scale_factor)
                        new_height = int(original_height * scale_factor)
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        resized_img.save(optimized_file, "JPEG", quality=current_quality, optimize=True)
                        optimized_size_kb = os.path.getsize(optimized_file) / 1024
                        
                        # それでも10KB未満の場合は、さらに拡大
                        if optimized_size_kb < min_size_kb:
                            scale_factor = 1.5  # 50%拡大
                            new_width = int(original_width * scale_factor)
                            new_height = int(original_height * scale_factor)
                            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            resized_img.save(optimized_file, "JPEG", quality=current_quality, optimize=True)
                            optimized_size_kb = os.path.getsize(optimized_file) / 1024
                    
                    logger.info(f"最小サイズ調整後: {optimized_size_kb:.2f}KB")
                    
                    # 元ファイルを削除
                    try:
                        os.remove(file_path)
                        logger.info(f"元ファイルを削除しました: {file_path}")
                    except Exception as delete_error:
                        logger.warning(f"元ファイルの削除に失敗しました: {delete_error}")
                    
                    return optimized_file
                
                # ファイルサイズが制限以下の場合は最適化不要（ただし解像度チェック）
                if file_size_mb <= max_size_mb:
                    # 画像サイズもチェック
                    if original_width <= max_dimension and original_height <= max_dimension:
                        logger.debug("画像サイズは要件を満たしており最適化不要です")
                        return file_path
                
                logger.info("画像ファイルが大きいため最適化を実施します")
                
                # リサイズが必要かチェック
                if original_width > max_dimension or original_height > max_dimension:
                    # アスペクト比を保持してリサイズ
                    ratio = min(max_dimension / original_width, max_dimension / original_height)
                    new_width = int(original_width * ratio)
                    new_height = int(original_height * ratio)
                    logger.info(f"リサイズ: {original_width}x{original_height} -> {new_width}x{new_height}")
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # JPEG形式で保存（品質設定）
                # 品質を下げながらサイズを調整
                save_quality = quality
                img.save(optimized_file, "JPEG", quality=save_quality, optimize=True)
                
                # ファイルサイズをチェック
                optimized_size_mb = os.path.getsize(optimized_file) / (1024 * 1024)
                optimized_size_kb = os.path.getsize(optimized_file) / 1024
                logger.info(f"最適化後のファイルサイズ: {optimized_size_kb:.2f}KB ({optimized_size_mb:.2f}MB)")
                
                # 最小サイズチェック（最適化後も10KB未満の場合は調整）
                if optimized_size_kb < min_size_kb:
                    logger.warning(f"最適化後も{min_size_kb}KB未満です（{optimized_size_kb:.2f}KB）。品質を上げます")
                    current_quality = min(save_quality + 20, 100)
                    img.save(optimized_file, "JPEG", quality=current_quality, optimize=True)
                    optimized_size_kb = os.path.getsize(optimized_file) / 1024
                    
                    # まだ10KB未満の場合は、解像度を上げる
                    if optimized_size_kb < min_size_kb:
                        logger.info(f"品質を上げても{min_size_kb}KB未満のため、解像度を上げます")
                        current_width, current_height = img.size
                        scale_factor = 1.2
                        new_width = int(current_width * scale_factor)
                        new_height = int(current_height * scale_factor)
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        resized_img.save(optimized_file, "JPEG", quality=current_quality, optimize=True)
                        optimized_size_kb = os.path.getsize(optimized_file) / 1024
                        logger.info(f"解像度上げ後: {optimized_size_kb:.2f}KB")
                
                # まだ大きい場合はさらに品質を下げる
                if optimized_size_mb > max_size_mb and save_quality > 50:
                    logger.info(f"ファイルサイズがまだ大きいため、品質を下げます")
                    for q in range(save_quality - 10, 49, -10):
                        img.save(optimized_file, "JPEG", quality=q, optimize=True)
                        optimized_size_mb = os.path.getsize(optimized_file) / (1024 * 1024)
                        optimized_size_kb = os.path.getsize(optimized_file) / 1024
                        logger.info(f"品質{q}で保存: {optimized_size_kb:.2f}KB ({optimized_size_mb:.2f}MB)")
                        if optimized_size_mb <= max_size_mb:
                            break
                        
                        # 最小サイズを維持
                        if optimized_size_kb < min_size_kb:
                            logger.warning(f"品質を下げすぎて{min_size_kb}KB未満になりました。品質を調整します")
                            break
                
                # 最適化後も大きい場合、さらにリサイズ
                if optimized_size_mb > max_size_mb:
                    logger.warning(f"品質を下げてもサイズが大きいため、さらにリサイズします")
                    current_size = optimized_size_mb
                    current_dim = max_dimension
                    while current_size > max_size_mb and current_dim > 400:
                        current_dim = int(current_dim * 0.8)
                        new_width = int(original_width * (current_dim / max(original_width, original_height)))
                        new_height = int(original_height * (current_dim / max(original_width, original_height)))
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        resized_img.save(optimized_file, "JPEG", quality=save_quality, optimize=True)
                        current_size = os.path.getsize(optimized_file) / (1024 * 1024)
                        current_size_kb = os.path.getsize(optimized_file) / 1024
                        logger.info(f"リサイズ後 ({new_width}x{new_height}): {current_size_kb:.2f}KB ({current_size:.2f}MB)")
                        
                        # 最小サイズを維持
                        if current_size_kb < min_size_kb:
                            logger.warning(f"リサイズで{min_size_kb}KB未満になりました。品質を上げます")
                            resized_img.save(optimized_file, "JPEG", quality=min(save_quality + 10, 100), optimize=True)
                            current_size_kb = os.path.getsize(optimized_file) / 1024
                            logger.info(f"品質調整後: {current_size_kb:.2f}KB")
                
                logger.info(f"最適化完了: {optimized_file}")
                
                # 元ファイルを削除
                try:
                    os.remove(file_path)
                    logger.info(f"元ファイルを削除しました: {file_path}")
                except Exception as delete_error:
                    logger.warning(f"元ファイルの削除に失敗しました: {delete_error}")
                
                return optimized_file
                
        except Exception as img_error:
            logger.error(f"画像の最適化に失敗しました: {img_error}")
            return file_path
            
    except Exception as e:
        logger.error(f"画像の最適化に失敗しました: {e}")
        return file_path
