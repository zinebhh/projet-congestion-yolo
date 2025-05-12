from app import create_app, db
from app.user_model import User
import sqlite3

app = create_app()

with app.app_context():
    db.create_all()
    print("Base de données et tables créées avec succès.")


