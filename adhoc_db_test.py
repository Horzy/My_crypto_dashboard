import sqlite3
conn = sqlite3.connect('crypto.db')
cur  = conn.cursor()
cur.execute("SELECT COUNT(*) FROM btc_history")
count = cur.fetchone()[0]
print(f"btc_history has {count} rows")
conn.close()
