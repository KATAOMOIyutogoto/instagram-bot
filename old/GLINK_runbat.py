import subprocess
import time
from pathlib import Path
import logging
from datetime import datetime
import sys
from enum import Enum

# 実行種別の定義
class ExecutionType(Enum):
   GLINK = "GLINK"
   GLINK_V2 = "GLINK_v2"
   GLINK_V3 = "GLINK_v3"

# エンコーディング設定
if sys.platform == 'win32':
   sys.stdout.reconfigure(encoding='utf-8')
   sys.stderr.reconfigure(encoding='utf-8')

"""
def setup_logger():
   # スクリプト情報を取得
   script_dir = Path(__file__).parent
   script_name = Path(__file__).stem
   
   # 現在の日付を取得
   current_date = datetime.now().strftime('%Y%m%d')
   
   # ログディレクトリのパスを作成
   log_dir = script_dir / 'log' / current_date
   log_dir.mkdir(parents=True, exist_ok=True)
   
   # ログファイル名を設定（スクリプト名_YYYYMMDD.log）
   log_file = log_dir / f'{script_name}_{current_date}.log'
   
   # ロギングの設定
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler(log_file, encoding='utf-8', mode='a'),
           logging.StreamHandler()
       ]
   )
   return logging.getLogger(__name__)
"""
class DailyRotatingFileHandler(logging.FileHandler):
    def __init__(self, script_dir, script_name, encoding='utf-8'):
        self.script_dir = script_dir
        self.script_name = script_name
        self.current_date = datetime.now().strftime('%Y%m%d')
        
        # 初期のログファイルパスを設定
        log_file = self._get_log_file_path()
        
        super().__init__(log_file, encoding=encoding, mode='a')

    def emit(self, record):
        # 現在の日付をチェック
        current_date = datetime.now().strftime('%Y%m%d')
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
        log_dir = self.script_dir / 'log' / self.current_date
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # ログファイル名を設定
        return str(log_dir / f'{self.script_name}_{self.current_date}.log')

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
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # カスタムファイルハンドラを追加
    file_handler = DailyRotatingFileHandler(script_dir, script_name, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # コンソールハンドラを追加
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
   
def execute_python_script(script_name, arg, process_id=None):
    """Pythonスクリプトを実行し、結果を返す"""
    global logger  # グローバルなloggerを使用
    
    script_dir = Path(__file__).parent
    script_path = str(script_dir / script_name)

    logger.info(f"{script_name}の実行を開始します")
    
    try:
        # コマンドの構築
        cmd = ["python", script_path, arg]
        if process_id is not None:  # プロセスIDが指定されている場合は追加
            cmd.append(str(process_id))
            
        process = subprocess.run(
            cmd,
            check=True,
            text=True,
            encoding='utf-8',
            cwd=str(script_dir)
        )

        logger.info(f"{script_name}が正常終了しました")
        return True

    except subprocess.CalledProcessError as e:
        #logger.info(f"{script_name}の終了コード: {e.returncode}")
        
        if e.returncode == 3:
            logger.info("アカウントロック、または自動化検出のため60分待機します")
            time.sleep(60*60)
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

def cleanup_media_folder(user_name,logger):
   try:
       # スクリプトのディレクトリを取得
       script_dir = Path(__file__).parent
       
       # media/user_nameのパスを生成
       target_dir = script_dir / 'media' / user_name
       
       # フォルダが存在しない場合は終了
       if not target_dir.exists():
           return True

       # フォルダ内のファイルとサブフォルダを全て削除
       for item in target_dir.glob('*'):
           if item.is_file():
               item.unlink()
           elif item.is_dir():
               import shutil
               shutil.rmtree(item)
               
       return True
       
   except Exception as e:
       logger.info(f"削除中にエラーが発生: {str(e)}")
       return False


def process_command(command_type, arg, logger):

   success = cleanup_media_folder(arg, logger)
   if success:
      logger.info("メディアフォルダを正常にクリーンアップしました")
   else:
      logger.info("メディアフォルダのクリーンアップに失敗しました")



   """コマンド種別に応じた処理を実行"""
   if command_type == ExecutionType.GLINK:
       logger.info(f"GLINK_storyフローを開始: {arg}")
       if execute_python_script("MEO.py", arg):
           execute_python_script("GBP.py", arg)
  
   elif command_type == ExecutionType.GLINK_V2:
       logger.info(f"GLINK_v2_postフローを開始: {arg}")

       process_id = datetime.now().strftime('%Y%m%d_%H%M%S')
       post_success = execute_python_script("post.py", arg, process_id)
       
       if post_success:
           post_gbp_success = execute_python_script("post_GBP.py", arg, process_id)
  
   elif command_type == ExecutionType.GLINK_V3:
       logger.info(f"GLINK_v3_story-postフローを開始: {arg}")

       logger.info("storyフローを開始します")       
       # MEO/GBPフロー
       meo_success = execute_python_script("MEO.py", arg)
       
       if meo_success:
           gbp_success = execute_python_script("GBP.py", arg)
       
       # POST/GBPフロー（MEO/GBPの結果に関わらず実行）
       process_id = datetime.now().strftime('%Y%m%d_%H%M%S')

       logger.info("postフローを開始します")
       post_success = execute_python_script("post.py", arg, process_id)
       
       if post_success:
           post_gbp_success = execute_python_script("post_GBP.py", arg, process_id)


def execute_commands(file_path, logger):
   try:
       # コマンドリストの読み込み
       with open(file_path, 'r', encoding='utf-8') as f:
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
                   
                   logger.info("sleep(60s)")
                   time.sleep(60)
                   
               except Exception as e:
                   logger.error(f"予期せぬエラーが発生しました: {str(e)}")
           
           #logger.info(f"実行サイクル #{execution_count} が完了しました")
           #logger.info("コマンドリストの先頭に戻ります...")
           
   except Exception as e:
       logger.error(f"コマンド実行プロセスでエラーが発生: {str(e)}")
       raise

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    file_path = script_dir / 'GLINK_LIST.txt'
    
    logger = setup_logger()
    
    # lock配下のファイルをチェックして削除
    lock_dir = script_dir / 'lock'
    if lock_dir.exists():
        lock_files = list(lock_dir.glob('*'))
        if lock_files:
            logger.info(f"既存のロックファイルを削除します（{len(lock_files)}件）")
            for lock_file in lock_files:
                try:
                    lock_file.unlink()
                    logger.info(f"ロックファイルを削除: {lock_file.name}")
                except Exception as e:
                    logger.error(f"ロックファイルの削除に失敗: {lock_file.name} - {e}")
    
    try:
        logger.info("スクリプトを開始しました")
        execute_commands(file_path, logger)
    except KeyboardInterrupt:
        logger.info("ユーザーによりスクリプトが終了されました")
    except Exception as e:
        logger.error(f"スクリプトエラー: {str(e)}")