from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)  # Assure-toi que cette ligne existe
    password = db.Column(db.String(120), nullable=False)
    fullname = db.Column(db.String(120))
    gender = db.Column(db.String(10))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))


    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
class VideoAnalysees(db.Model):
    __tablename__ = 'video_analysees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    analysis_date = db.Column(db.DateTime)
    filename = db.Column(db.String)  # Assurez-vous que cette ligne existe
    type = db.Column(db.String)
    nb_vehicules = db.Column(db.Integer)
    vitesse_moyenne = db.Column(db.Float)
    etat = db.Column(db.String)


