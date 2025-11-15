import os
import sqlite3
import logging
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def setup_logger():
    # スクリプトのファイル名を取得（拡張子なし）
    script_name = Path(__file__).stem
    
    # 現在の日付を取得
    current_date = datetime.now().strftime('%Y%m')
    
    # logディレクトリと日付ディレクトリのパスを作成
    log_dir = Path(__file__).parent / 'log' / current_date
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 現在の日付でログファイル名を生成
    log_file = log_dir / f'{script_name}_{current_date}.log'
    
    # ログフォーマットの設定
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # ファイルハンドラの設定
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # ロガーの設定
    logger = logging.getLogger('DatabaseCleanup')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    
    # ログファイルに区切り線と開始メッセージを書き込む
    separator = "=" * 80
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if os.path.exists(log_file):
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{separator}\n")
    
    return logger

# 90日前
def cleanup_old_records(logger):
    DBNAME = os.getenv('DB_NAME')
    TABLENAME = os.getenv('TABLE_NAME')
    conn = None
    
    try:
        logger.info("処理開始")
        logger.info(f"データベース: {DBNAME}, テーブル: {TABLENAME}")
        
        conn = sqlite3.connect(DBNAME)
        cursor = conn.cursor()
        
        # 現在の日時から24時間前の日時を計算
        #cutoff_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        cutoff_time = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')


        #全削除用
        #cutoff_time = datetime.now()
        logger.info(f"削除基準時刻: {cutoff_time}")
        
        # 削除対象のレコード数を確認
        cursor.execute(f"""
            SELECT COUNT(*) FROM {TABLENAME}
            WHERE created < ?
        """, (cutoff_time,))
        target_count = cursor.fetchone()[0]
        logger.info(f"削除対象レコード数: {target_count}")
        
        # レコードを削除
        cursor.execute(f"""
            DELETE FROM {TABLENAME}
            WHERE created < ?
        """, (cutoff_time,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # 残っているレコードを確認
        cursor.execute(f"SELECT COUNT(*) FROM {TABLENAME}")
        remaining_count = cursor.fetchone()[0]
        
        logger.info(f"削除完了したレコード数: {deleted_count}")
        logger.info(f"残りのレコード数: {remaining_count}")
        logger.info("クリーンアップ処理が正常に完了しました")
        
    except sqlite3.Error as e:
        error_msg = f"データベースエラーが発生しました: {e}"
        logger.error(error_msg)
        print(error_msg)
        if conn:
            conn.rollback()
    except Exception as e:
        error_msg = f"予期せぬエラーが発生しました: {e}"
        logger.error(error_msg)
        print(error_msg)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
        logger.info("処理終了")

# 1月前
def cleanup_old_logs(logger):
    try:
        # logディレクトリのパスを取得
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
        logger.info(f'ログディレクトリのクリーンアップを開始: {log_dir}')
        
        # 現在の日時を取得
        current_date = datetime.now()
        
        # 6ヶ月前の年月を計算
        current_month = current_date.year * 12 + current_date.month - 1  # 0-based monthに変換
        six_months_ago = current_month - 6
        threshold_year_6m = six_months_ago // 12
        threshold_month_6m = (six_months_ago % 12) + 1  # 1-based monthに戻す
        threshold_str_6m = f"{threshold_year_6m}{threshold_month_6m:02d}"
        
        # 30日前の日付を計算
        threshold_date_30d = current_date - timedelta(days=30)
        threshold_str_30d = threshold_date_30d.strftime('%Y%m%d')
        
        deleted_count = {'monthly': 0, 'daily': 0}
        
        # logディレクトリ内のフォルダを処理
        for item in os.listdir(log_dir):
            item_path = os.path.join(log_dir, item)
            
            # ディレクトリのみを処理
            if not os.path.isdir(item_path):
                continue
            
            try:
                if len(item) == 6 and item.isdigit():
                    # YYYYMM形式のフォルダを処理
                    if item <= threshold_str_6m:
                        shutil.rmtree(item_path)
                        deleted_count['monthly'] += 1
                        logger.info(f'6ヶ月以前の月次フォルダを削除: {item}')
                        
                elif len(item) == 8 and item.isdigit():
                    # YYYYMMDD形式のフォルダを処理
                    if item <= threshold_str_30d:
                        shutil.rmtree(item_path)
                        deleted_count['daily'] += 1
                        logger.info(f'30日以前の日次フォルダを削除: {item}')
            
            except Exception as e:
                logger.error(f'フォルダ削除中にエラーが発生: {item} - {str(e)}')
                continue
        
        logger.info(f'ログディレクトリのクリーンアップ完了。月次フォルダ: {deleted_count["monthly"]}個、日次フォルダ: {deleted_count["daily"]}個を削除')
        return True
        
    except Exception as e:
        logger.error(f'ログクリーンアップ処理でエラーが発生: {str(e)}')
        return False

# 7日前
def cleanup_old_medias(logger):   
    try:
        # media_bkディレクトリのパスを取得
        media_bk_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'media_bk')
        logger.info(f'メディアバックアップのクリーンアップを開始: {media_bk_dir}')
        
        # 現在の日時と1ヶ月前の日時を取得
        current_date = datetime.now()
        one_month_ago = current_date - timedelta(days=7)
        logger.debug(f'削除基準日時: {one_month_ago.strftime("%Y-%m-%d %H:%M:%S")}')
        
        deleted_count = {'jpg': 0, 'mp4': 0}
        
        # media_bkディレクトリ内のファイルを処理
        for filename in os.listdir(media_bk_dir):
            if not (filename.endswith('.jpg') or filename.endswith('.mp4')):
                continue
            
            try:
                # ファイル名から日時部分を抽出 (.jpgまたは.mp4を除いた末尾14桁)
                extension = '.jpg' if filename.endswith('.jpg') else '.mp4'
                date_str = filename[:-len(extension)][-14:]  # YYYYMMDDhhmmss
                
                if len(date_str) == 14:  # 日時形式の確認
                    file_date = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    
                    if file_date <= one_month_ago:
                        file_path = os.path.join(media_bk_dir, filename)
                        os.remove(file_path)
                        file_type = 'jpg' if extension == '.jpg' else 'mp4'
                        deleted_count[file_type] += 1
                        logger.info(f'古いメディアファイルを削除: {filename} '
                                  f'(作成日時: {file_date.strftime("%Y-%m-%d %H:%M:%S")})')
                    else:
                        logger.debug(f'保持するメディアファイル: {filename} '
                                   f'(作成日時: {file_date.strftime("%Y-%m-%d %H:%M:%S")})')
                else:
                    logger.warning(f'ファイル名の日時形式が不正: {filename}')
                    
            except ValueError as ve:
                logger.warning(f'ファイル名の日時解析に失敗: {filename}')
                continue
            except Exception as e:
                logger.error(f'ファイル削除中にエラーが発生: {filename} - {str(e)}')
                continue
        
        logger.info(f'メディアファイルのクリーンアップ完了。画像: {deleted_count["jpg"]}件、'
                   f'動画: {deleted_count["mp4"]}件を削除')
        return True
        
    except Exception as e:
        logger.error(f'メディアクリーンアップ処理でエラーが発生: {str(e)}')
        return False

# 7日前
def cleanup_old_description(logger):
    try:
        # descriptionディレクトリのパスを取得
        description_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'media', 'media_bk', 'description')
        logger.info(f'説明文バックアップのクリーンアップを開始: {description_dir}')

        # 現在の日時と7日前の日時を取得
        current_date = datetime.now()
        seven_days_ago = current_date - timedelta(days=7)
        logger.debug(f'削除基準日時: {seven_days_ago.strftime("%Y-%m-%d %H:%M:%S")}')

        # descriptionディレクトリが存在しない場合は終了
        if not os.path.exists(description_dir):
            logger.warning(f'ディレクトリが存在しません: {description_dir}')
            return False

        deleted_count = 0
        # descriptionディレクトリ内のファイルを処理
        for filename in os.listdir(description_dir):
            file_path = os.path.join(description_dir, filename)
            try:
                # ファイルの作成日時を取得
                file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                
                if file_creation_time <= seven_days_ago:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f'古い説明文ファイルを削除: {filename} '
                              f'(作成日時: {file_creation_time.strftime("%Y-%m-%d %H:%M:%S")})')
                #else:
                #    logger.debug(f'保持するファイル: {filename} '
                #               f'(作成日時: {file_creation_time.strftime("%Y-%m-%d %H:%M:%S")})')

            except Exception as e:
                logger.error(f'ファイル処理中にエラーが発生: {filename} - {str(e)}')
                continue

        logger.info(f'説明文ファイルのクリーンアップ完了。{deleted_count}件のファイルを削除')
        return True

    except Exception as e:
        logger.error(f'説明文クリーンアップ処理でエラーが発生: {str(e)}')
        return False

# 1日前
def cleanup_old_description_2(logger):
    try:
        # メディアのルートディレクトリを取得
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')
        logger.info(f'説明文バックアップのクリーンアップを開始: {base_dir}')

        # 削除基準時刻（1日前）を設定
        one_day_ago = datetime.now() - timedelta(days=1)
        logger.debug(f'削除基準日時: {one_day_ago.strftime("%Y-%m-%d %H:%M:%S")}')

        deleted_count = 0
        # mediaディレクトリ内の各フォルダを処理
        for media_dir in os.listdir(base_dir):
            description_dir = os.path.join(base_dir, media_dir, 'description')
            
            # descriptionディレクトリが存在しない場合はスキップ
            if not os.path.exists(description_dir):
                continue

            #logger.info(f'処理中のディレクトリ: {description_dir}')

            # descriptionディレクトリ内のファイルを処理
            for filename in os.listdir(description_dir):
                try:
                    file_path = os.path.join(description_dir, filename)
                    
                    # ファイルの作成日時を取得
                    file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_creation_time <= one_day_ago:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f'古いファイルを削除: {file_path} '
                                  f'(作成日時: {file_creation_time.strftime("%Y-%m-%d %H:%M:%S")})')
                    else:
                        logger.debug(f'保持するファイル: {file_path} '
                                   f'(作成日時: {file_creation_time.strftime("%Y-%m-%d %H:%M:%S")})')
                        
                except Exception as e:
                    logger.error(f'ファイル処理中にエラーが発生: {file_path} - {str(e)}')
                    continue

        logger.info(f'説明文ファイルのクリーンアップ完了。{deleted_count}件のファイルを削除')
        return True

    except Exception as e:
        logger.error(f'説明文クリーンアップ処理でエラーが発生: {str(e)}')
        return False

if __name__ == "__main__":
    logger = setup_logger()
    cleanup_old_records(logger)
    cleanup_old_logs(logger)
    cleanup_old_medias(logger)
    cleanup_old_description(logger)
    cleanup_old_description_2(logger)
