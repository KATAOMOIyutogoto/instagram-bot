import sqlite3

dbname = 'MEO.db'
conn = sqlite3.connect(dbname)
cur = conn.cursor()

# MEOテーブルの作成
#cur.execute('''
#    CREATE TABLE IF NOT EXISTS MEO (
#        id INTEGER NOT NULL,
#        cache_key TEXT NOT NULL,
#        media_url TEXT,
#        posted DATETIME,
#        created DATETIME DEFAULT (DATETIME(CURRENT_TIMESTAMP,'localtime')),
#        PRIMARY KEY (id, cache_key)
#    )
#    ''')

cur.execute('''
        CREATE TABLE IF NOT EXISTS MEO (
            user_name TEXT,
            cache_key TEXT,
            media_url TEXT,
            created DATETIME DEFAULT (DATETIME(CURRENT_TIMESTAMP,'localtime')),
            PRIMARY KEY (user_name, cache_key)
        )
    ''')

# インデックスの作成
# cur.execute('CREATE INDEX IF NOT EXISTS idx_meo_posted ON MEO(posted)')
cur.execute('CREATE INDEX IF NOT EXISTS idx_meo_created ON MEO(created)')

conn.commit()
conn.close()