import sqlite3

conn = sqlite3.connect(r'C:\python\project-root\app\database.db')
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, email, username FROM users")
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print("❌ Erreur SQL :", e)

conn.close()

