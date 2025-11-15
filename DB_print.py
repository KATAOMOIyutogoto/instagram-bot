import sqlite3

def truncate_string(text, max_length):
    """文字列を指定の長さで省略する"""
    if isinstance(text, str) and len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

def display_table(db_path, table_name, max_width=30):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # テーブル情報の取得
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cur.fetchall()]
        
        if not columns:
            print(f"\nテーブル '{table_name}' が存在しないか、カラムがありません。")
            return
            
        # データの取得
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        
        # カラム幅の設定（空テーブルの場合はカラム名の長さを使用）
        if rows:
            col_widths = [min(max_width, max(len(str(col)), 
                         max(len(str(row[i])) for row in rows)))
                         for i, col in enumerate(columns)]
        else:
            col_widths = [min(max_width, len(str(col))) for col in columns]
        
        # テーブル名の表示
        print(f"\nTable: {table_name}")
        
        # 区切り線の作成
        border = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
        
        # ヘッダーの表示
        print(border)
        header = "|" + "|".join(f" {col:<{width}} " 
                for col, width in zip(columns, col_widths)) + "|"
        print(header)
        print(border)
        
        # データの表示
        if not rows:
            print(f"| No data found {' ' * (sum(col_widths) + len(columns) * 2 - 13)}|")
            print(border)
        else:
            for row in rows:
                row_display = []
                for value, width in zip(row, col_widths):
                    truncated_value = truncate_string(str(value), width)
                    row_display.append(f" {truncated_value:<{width}} ")
                
                print("|" + "|".join(row_display) + "|")
                print(border)
            
    except sqlite3.Error as e:
        print(f"エラーが発生しました: {e}")
    finally:
        conn.close()

# 使用例
if __name__ == "__main__":
    db_path = 'MEO.db'
    table_name = 'meo'
    display_table(db_path, table_name, max_width=50)