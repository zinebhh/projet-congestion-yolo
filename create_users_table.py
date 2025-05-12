import sqlite3

# Connexion à la base de données
conn = sqlite3.connect(r'C:\python\project-root\app\database.db')
cursor = conn.cursor()

# Création de la table 'users'
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    fullname TEXT,
    gender TEXT,
    city TEXT,
    state TEXT
)
''')

# Création de la table 'video_analysees'
cursor.execute('''
CREATE TABLE IF NOT EXISTS video_analysees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    analysis_date TEXT,
    filename TEXT,
    type TEXT,
    nb_vehicules INTEGER,
    vitesse_moyenne REAL,
    etat TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

conn.commit()
conn.close()

print("✅ Tables 'users' et 'video_analysees' créées avec succès.")
