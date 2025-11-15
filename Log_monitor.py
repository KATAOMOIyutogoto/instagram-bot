import os
import requests
import logging
from pathlib import Path
from datetime import datetime, timedelta
import re

class LogMonitor:
    def __init__(self, post_url: str):
        self.script_dir = Path(__file__).parent

        self.current_date = datetime.now().strftime('%Y%m%d')
        
        # 日付ごとのログディレクトリを設定
        self.log_directory = self.script_dir / 'log' / self.current_date
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.post_url = post_url
        self.script_name = Path(__file__).stem
        
        # 自身のログファイル名を設定
        self.log_file_name = f"{self.script_name}_{self.current_date}.log"
        self.log_file_path = self.log_directory / self.log_file_name
        
        # 区切り線とタイムスタンプを書き込む
        self.write_separator()
        
        # ロギングの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file_path, encoding='utf-8', mode='a'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 古いログファイルの削除を実行
        #self.cleanup_old_logs()
        
        self.logger.info(f"監視開始: {self.log_directory}")
        self.logger.info(f"監視日付: {self.current_date}")

    def write_separator(self):
        """ログファイルに区切り線とタイムスタンプを書き込む"""
        separator = "=" * 80
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"{separator}\n")

    def is_target_log_file(self, file_path: Path) -> bool:
        """監視対象のログファイルかどうかを判定する"""
        # 自身のログファイルは除外
        if file_path.name == self.log_file_name:
            return False
            
        # ファイル名から日付を抽出
        match = re.search(r'_(\d{8})\.log$', file_path.name)
        if match:
            file_date = match.group(1)
            # 同じ日付のファイルのみ対象とする
            return file_date == self.current_date
            
        return False

    def read_log_file(self, file_path: Path) -> bool:
        """ログファイルを読み込み、ERRが含まれているかチェックする"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'ERROR' in line:
                        return True
            return False
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー {file_path}: {str(e)}")
            return False

    def send_error_notification(self, error_files_str: str) -> bool:
        """エラーが見つかったファイル名をPOSTリクエストで送信する"""
        payload = {
            'error_files': error_files_str  # 改行区切りのファイル名リスト
        }
        
        try:
            response = requests.post(self.post_url, json=payload)
            if response.status_code == 200:
                self.logger.info(f"通知送信成功: \n{error_files_str}")
                return True
            else:
                self.logger.error(f"通知送信失敗: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"POST リクエストエラー: {str(e)}")
            return False

    def move_to_err_directory(self, log_file: Path) -> bool:
        """エラーが見つかったログファイルをerrディレクトリに移動する"""
        try:
            self.current_date = datetime.now().strftime('%Y%m%d')
            
            # 日付ごとのerrディレクトリを設定
            err_directory = self.script_dir / 'err' / self.current_date
            
            # errディレクトリが存在しない場合は作成（親ディレクトリも含めて）
            err_directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"errディレクトリを確認しました: {err_directory}")
            
            # 移動先のパスを設定
            destination = err_directory / log_file.name
            
            # 同名ファイルが存在する場合は、タイムスタンプを付加して名前を変更
            if destination.exists():
                timestamp = datetime.now().strftime('%H%M%S')
                new_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
                destination = err_directory / new_name
            
            # ファイルを移動
            log_file.rename(destination)
            self.logger.info(f"エラーログを移動しました: {log_file.name} -> {destination.name}")
            return True
            
        except Exception as move_error:
            self.logger.error(f"ファイル移動エラー {log_file.name}: {str(move_error)}")
            return False

    def check_logs(self):
        """ログディレクトリをチェックし、エラーを含むファイルを検出する"""
        try:
            # 全ログファイルを取得
            all_log_files = list(self.log_directory.glob('*.log'))
            self.logger.info(f"ログディレクトリ内のファイル総数: {len(all_log_files)}")
            
            # 監視対象のログファイルをフィルタリング
            target_log_files = [f for f in all_log_files if self.is_target_log_file(f)]
            self.logger.info(f"監視対象ファイル数: {len(target_log_files)}")
            
            if not target_log_files:
                self.logger.info(f"{self.current_date}の日付を持つ監視対象ログファイルが見つかりません")
                return
            
            error_files = []
            error_files_count = 0
            moved_files_count = 0
            
            # エラーチェック
            for log_file in target_log_files:
                if self.read_log_file(log_file):
                    error_files.append(log_file)
                    error_files_count += 1
            
            # エラーが見つかったファイルの処理
            if error_files:
                self.logger.info(f"エラーが見つかったファイル数: {error_files_count}")
                
                # すべてのエラーファイル名を改行区切りの1つの文字列にまとめる
                error_files_str = "\n".join([f.name for f in error_files])
                
                # まとめて通知を送信
                if self.send_error_notification(error_files_str):
                    # 通知成功後、ファイルを移動
                    for error_file in error_files:
                        if self.move_to_err_directory(error_file):
                            moved_files_count += 1
                
                self.logger.info(f"errディレクトリに移動したファイル数: {moved_files_count}")
                
                # 移動に失敗したファイルがある場合
                if moved_files_count < error_files_count:
                    failed_count = error_files_count - moved_files_count
                    self.logger.warning(f"移動に失敗したファイル数: {failed_count}")
            else:
                self.logger.info("エラーは検出されませんでした")
            
        except Exception as e:
            self.logger.error(f"チェック処理エラー: {str(e)}")
            raise

    def count_form_submissions(self):
        """ログファイルから「フォームを送信しました」の件数を集計する"""
        try:
            # 全ログファイルを取得
            all_log_files = list(self.log_directory.glob('*.log'))
            self.logger.info(f"集計対象のファイル総数: {len(all_log_files)}")
            
            # 該当のログがあるファイルを格納
            files_with_submissions = []
            total_submissions = 0
            
            for log_file in all_log_files:
                try:
                    submission_count = 0
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if 'フォームを送信しました' in line:
                                submission_count += 1
                    
                    if submission_count > 0:
                        files_with_submissions.append({
                            'file_name': log_file.name,
                            'count': submission_count
                        })
                        total_submissions += submission_count
                        
                except Exception as e:
                    self.logger.error(f"ファイル読み込みエラー {log_file.name}: {str(e)}")
                    continue
            
            # 結果の出力
            if files_with_submissions:
                self.logger.info(f"\n送信ログ集計結果:")
                self.logger.info(f"対象ファイル数: {len(files_with_submissions)}")
                self.logger.info(f"総送信数: {total_submissions}")
                self.logger.info("\nファイルごとの送信数:")
                for file_info in files_with_submissions:
                    self.logger.info(f"- {file_info['file_name']}: {file_info['count']}件")
            else:
                self.logger.info("送信ログは見つかりませんでした")
                
            return {
                'files_count': len(files_with_submissions),
                'total_submissions': total_submissions,
                'files_detail': files_with_submissions
            }
            
        except Exception as e:
            self.logger.error(f"集計処理エラー: {str(e)}")
            raise

def main():
    # 通知先URLの設定
    POST_URL = "https://hooks.zapier.com/hooks/catch/19547385/29ft0n7/"  # 通知先URLを実際のエンドポイントに変更してください
    
    try:
        monitor = LogMonitor(POST_URL)
        monitor.check_logs()

        monitor.count_form_submissions()

    except Exception as e:
        logging.error(f"実行エラー: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()