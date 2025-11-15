import os
import sqlite3
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def delete_records(cur, user_name):
    try:
        # パラメータはタプルで渡す必要があるため、カンマを追加
        # メディアURL列も指定しておく
        cur.execute('''
            SELECT user_name, media_url 
            FROM MEO 
            WHERE user_name = ?
        ''', (user_name,))  # カンマを追加して1要素のタプルにする
        
        # 削除前のレコードを取得して確認
        records = cur.fetchall()
        if not records:
            print("削除対象のレコードが見つかりませんでした")
            return False
            
        print(f"削除対象のレコード数: {len(records)}")
        for record in records:
            print(f"- ユーザー名: {record[0]}, メディアURL: {record[1]}")
            
        # 削除クエリの実行
        cur.execute('''
            DELETE FROM MEO
            WHERE user_name = ?
        ''', (user_name,))  # カンマを追加して1要素のタプルにする
        
        # 削除された行数を取得
        rows_affected = cur.rowcount
        
        if rows_affected > 0:
            print(f"レコードの削除に成功しました。削除された行数: {rows_affected}")
            return True
        else:
            print("指定された条件に一致するレコードが見つかりませんでした")
            return False
            
    except sqlite3.Error as e:
        print(f"レコード削除中にエラーが発生しました: {e}")
        return False

def delete_meo_record(cur, user_name, cache_key):
    try:
        # 削除クエリの実行
        cur.execute('''
            DELETE FROM MEO 
            WHERE user_name = ? AND cache_key = ?
        ''', (user_name, cache_key))
        
        # 削除された行数を取得
        rows_affected = cur.rowcount
        
        if rows_affected > 0:
            print(f"Record deleted successfully. Rows affected: {rows_affected}")
            return True
        else:
            print("No record found with the specified keys")
            return False

    except sqlite3.Error as e:
        print(f"Error deleting record: {e}")
        return False

# 使用例
try:

    DBNAME = os.getenv('DB_NAME')
    TABLENAME = os.getenv('TABLE_NAME')
    conn = None

    conn = sqlite3.connect(DBNAME)
    cur = conn.cursor()


    # データベース接続とカーソル作成は事前に行われていると仮定
    user_name = "lienlien_770"
    cache_key = "MzUxNjc4NTQ5MTIxNzk2OTI5NQ==.3-ccb7-5"
    
    # 削除実行
    #success = delete_meo_record(cur, user_name, cache_key)
    success = delete_records(cur, user_name)

    # コミット
    if success:
        conn.commit()

except sqlite3.Error as e:
    print(f"Database error: {e}")
    conn.rollback()
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()