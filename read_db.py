import sqlite3
conn = sqlite3.connect(r'D:\anonym\session-backup\kilo.db.backup')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
print('Tables:', c.fetchall())