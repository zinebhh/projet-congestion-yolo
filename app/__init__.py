# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# import os

# db = SQLAlchemy()

# def create_app():
#     app = Flask(__name__, template_folder='../templates', static_folder='../static')
#     app.config['SECRET_KEY'] = 'your-secret-key'

#     basedir = os.path.abspath(os.path.dirname(__file__))
#     app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "database.db")}'
#     app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
#     db.init_app(app)

#     with app.app_context():
#         from . import routes  # Assure-toi que routes.py existe dans ce dossier
#         db.create_all()

#     return app
