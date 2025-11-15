import logging
import os
import subprocess
import sys
import time
import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# 実行種別の定義
class ExecutionType(Enum):
    GLINK = "GLINK"
    GLINK_V2 = "GLINK_v2"
    GLINK_V3 = "GLINK_v3"


# エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class DailyRotatingFileHandler(logging.FileHandler):
    def __init__(self, script_dir, script_name, encoding="utf-8"):
        self.script_dir = script_dir
        self.script_name = script_name
        self.current_date = datetime.now().strftime("%Y%m%d")

        # 初期のログファイルパスを設定
        log_file = self._get_log_file_path()

        super().__init__(log_file, encoding=encoding, mode="a")

    def emit(self, record):
        # 現在の日付をチェック
        current_date = datetime.now().strftime("%Y%m%d")
        if current_date != self.current_date:
            # 日付が変わっていれば、新しいログファイルに切り替え
            self.current_date = current_date
            self.close()  # 現在のファイルを閉じる

            # 新しいログファイルを設定
            new_file = self._get_log_file_path()
            self.baseFilename = new_file

            if self.stream:
                self.stream.close()
            self.stream = self._open()

        super().emit(record)

    def _get_log_file_path(self):
        # ログディレクトリのパスを作成
        log_dir = self.script_dir / "log" / self.current_date
        log_dir.mkdir(parents=True, exist_ok=True)

        # ログファイル名を設定
        return str(log_dir / f"{self.script_name}_{self.current_date}.log")


### loggerセットアップ ###
def setup_logger():
    # スクリプト情報を取得
    script_dir = Path(__file__).parent
    script_name = Path(__file__).stem

    # ロギングの設定
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 既存のハンドラをクリア
    logger.handlers.clear()

    # フォーマッタの設定
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # カスタムファイルハンドラを追加
    file_handler = DailyRotatingFileHandler(script_dir, script_name, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # コンソールハンドラを追加
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


### コマンド実行 ###
def execute_commands(file_path, logger):
    try:
        # コマンドリストの読み込み
        with open(file_path, "r", encoding="utf-8") as f:
            commands = [line.strip().split() for line in f.readlines() if line.strip()]

        logger.info(f"コマンドファイルを読み込みました: {file_path}")
        logger.info(f"コマンド総数: {len(commands)}")

        last_date = datetime.now().date()
        execution_count = 0

        while True:
            separator = "=" * 80
            logger.info(separator)

            execution_count += 1
            logger.info(f"実行サイクル #{execution_count} を開始")

            # 日付が変わったかチェック
            current_date = datetime.now().date()
            if current_date != last_date:
                logger.info("日付が変更されました。ログファイルを更新します...")
                logger = setup_logger()
                last_date = current_date

            # コマンドの実行
            for i, command in enumerate(commands, 1):
                if len(command) != 2:
                    logger.error(f"不正なコマンド形式: {' '.join(command)}")
                    continue

                cmd_type, arg = command
                try:
                    logger.info(separator)
                    logger.info(f"{i}/{len(commands)}: {' '.join(command)}")

                    try:
                        execution_type = ExecutionType(cmd_type)
                        process_command(execution_type, arg, logger)

                    except ValueError:
                        logger.error(f"未知のコマンド種別: {cmd_type}")

                    logger.info("sleep(60)")
                    time.sleep(60)

                except Exception as e:
                    logger.error(f"予期せぬエラーが発生しました: {str(e)}")

    except Exception as e:
        logger.error(f"コマンド実行プロセスでエラーが発生: {str(e)}")
        raise


### コマンド分岐 ###
def process_command(command_type, arg, logger):
    success = cleanup_media_folder(arg, logger)
    if success:
        logger.info("メディアフォルダを正常にクリーンアップしました")
    else:
        logger.info("メディアフォルダのクリーンアップに失敗しました")

    business_ids = get_business_ids(arg)
    if not business_ids:
        logger.error("Business IDが見つかりません")
        return False
    logger.info(f"GBP数: {len(business_ids)}, GBP: {business_ids}")

    """コマンド種別に応じた処理を実行"""
    ### GLINK_V1 ###
    if command_type == ExecutionType.GLINK:
        logger.info(f"GLINK_storyフローを開始: {arg}")

        process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"process_id: {process_id}")

        if execute_python_script("story.py", arg, process_id):
            for business_id in business_ids:
                execute_python_script("postGBP.py", "story", arg, business_id, process_id)

    ### GLINK_V2 ###
    elif command_type == ExecutionType.GLINK_V2:
        logger.info(f"GLINK_v2_postフローを開始: {arg}")

        process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"process_id: {process_id}")

        post_success = execute_python_script("post.py", arg, process_id)

        if post_success:
            for business_id in business_ids:
                post_gbp_success = execute_python_script("postGBP.py", "post", arg, business_id, process_id)

    ### GLINK_V3 ###
    elif command_type == ExecutionType.GLINK_V3:
        logger.info(f"GLINK_v3_story-postフローを開始: {arg}")

        # STORY/GBPフロー
        logger.info("storyフローを開始します")
        process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"process_id: {process_id}")

        meo_success = execute_python_script("story.py", arg, process_id)

        if meo_success:
            for business_id in business_ids:
                gbp_success = execute_python_script("postGBP.py", "story", arg, business_id, process_id)

        # バックアップ処理
        if backup_media_files(arg):
            logger.info("メディアファイルのバックアップが完了しました")
        else:
            logger.error("メディアファイルのバックアップに失敗しました")

        if backup_temp_file(arg, process_id):
            logger.info("説明文ファイルのバックアップが完了しました")
        else:
            logger.error("説明文ファイルのバックアップに失敗しましたss")

        # POST/GBPフロー（MEO/GBPの結果に関わらず実行）
        logger.info("postフローを開始します")
        process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"process_id: {process_id}")

        post_success = execute_python_script("post.py", arg, process_id)

        if post_success:
            for business_id in business_ids:
                post_gbp_success = execute_python_script("postGBP.py", "post", arg, business_id, process_id)

    # 共通のメディアファイルバックアップ処理
    if backup_media_files(arg):
        logger.info("メディアファイルのバックアップが完了しました")
    else:
        logger.error("メディアファイルのバックアップに失敗しました")

    if backup_temp_file(arg, process_id):
        logger.info("説明文ファイルのバックアップが完了しました")
    else:
        logger.error("説明文ファイルのバックアップに失敗しましたsss")


### メディアクリーンアップ ###
def cleanup_media_folder(user_name, logger):
    try:
        # スクリプトのディレクトリを取得
        script_dir = Path(__file__).parent

        # media/user_nameのパスを生成
        target_dir = script_dir / "media" / user_name

        # フォルダが存在しない場合は終了
        if not target_dir.exists():
            return True

        # フォルダ内のファイルとサブフォルダを全て削除
        for item in target_dir.glob("*"):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil

                shutil.rmtree(item)

        return True

    except Exception as e:
        logger.info(f"削除中にエラーが発生: {str(e)}")
        return False


### ビジネスID取得 ###
def get_business_ids(username):
    business_ids = []

    # 基本のbusiness_idを追加
    base_id = os.getenv(username)
    if base_id:
        business_ids.append(base_id)

    # 追加のbusiness_idを確認
    counter = 2
    while True:
        next_id = os.getenv(f"{username}_num{counter}")
        if next_id:
            business_ids.append(next_id)
            counter += 1
        else:
            break

    return business_ids


### Python実行_v2 ###
def execute_python_script(script_name, *args):
    """Pythonスクリプトを実行し、結果を返す

    Args:
        script_name (str): 実行するスクリプトの名前
        *args: スクリプトに渡す任意の数の引数
    """
    global logger

    script_dir = Path(__file__).parent
    script_path = str(script_dir / script_name)

    logger.info(f"{script_name}の実行を開始します")

    try:
        # コマンドの構築
        cmd = ["python", script_path]
        # 全ての引数を文字列に変換して追加
        cmd.extend(str(arg) for arg in args)

        process = subprocess.run(cmd, check=True, text=True, encoding="utf-8", cwd=str(script_dir))

        logger.info(f"{script_name}が正常終了しました")
        return True

    except subprocess.CalledProcessError as e:
        if e.returncode == 3:
            logger.info("アカウントロック、または自動化検出のため60分待機します")
            time.sleep(60 * 60)
            return False
        elif e.returncode == 1:
            logger.info(f"{script_name}で終了コード1でした")
            return False
        else:
            logger.error(f"{script_name}が予期せぬエラーで終了しました: 終了コード {e.returncode}")
            return False

    except Exception as e:
        logger.error(f"{script_name}の実行中に予期せぬエラーが発生: {e}")
        return False


### メディアバックアップ ###
def backup_media_files(username):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        source_dir = os.path.join(script_dir, "media", username)

        # フォルダが存在しない場合は成功として扱う
        if not os.path.exists(source_dir):
            return True

        media_dir = os.path.join(script_dir, "media")
        backup_dir = os.path.join(media_dir, "media_bk")

        # メディアファイルの拡張子
        media_extensions = (".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi")

        # ディレクトリ内のファイルを処理
        files_moved = 0
        for filename in os.listdir(source_dir):
            if filename.lower().endswith(media_extensions):
                source_path = os.path.join(source_dir, filename)
                backup_path = os.path.join(backup_dir, filename)

                # ファイルを移動
                shutil.move(source_path, backup_path)
                files_moved += 1
                print(f"移動完了: {filename}")

        print(f"合計 {files_moved} 個のファイルを移動しました")
        return True

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return False


### 一時ファイルバックアップ ###
def backup_temp_file(username, process_id):
    # 元のファイルパス
    # ★パスを変えないといけない★
    description_dir = os.path.join("media", username, "description")
    temp_file_path = os.path.join(description_dir, f"{process_id}")
    # ファイルが存在しない場合は成功として扱う
    if not os.path.exists(temp_file_path):
        return True

    # バックアップディレクトリのパス
    backup_dir = os.path.join("media", "media_bk", "description")

    # タイムスタンプを含むバックアップファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file_name = f"{username}_{process_id}_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_file_name)

    try:
        shutil.move(temp_file_path, backup_path)
        return True
    except Exception as e:
        print(f"バックアップ作成エラー: {str(e)}")
        return False


if __name__ == "__main__":

    subprocess.run("taskkill /F /IM chrome.exe", shell=True)

    script_dir = Path(__file__).parent
    file_path = script_dir / "GLINK_LIST.txt"

    logger = setup_logger()
    print(file_path)
    try:
        logger.info("スクリプトを開始しました")
        execute_commands(file_path, logger)
    except KeyboardInterrupt:
        logger.info("ユーザーによりスクリプトが終了されました")
    except Exception as e:
        logger.error(f"スクリプトエラー: {str(e)}")
