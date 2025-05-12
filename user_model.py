# # user_model.py
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import UserMixin
# from datetime import datetime
# from werkzeug.security import generate_password_hash, check_password_hash


# db = SQLAlchemy()


# class User(UserMixin, db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(150))
#     email = db.Column(db.String(150), unique=True)
#     password = db.Column(db.String(150))

#     def get_id(self):
#         return str(self.id)
#     def set_password(self, password):
#         self.password = generate_password_hash(password)

#     def check_password(self, password):
#         return check_password_hash(self.password, password)


# class VideoAnalysis(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     filename = db.Column(db.String(200), nullable=False)
#     result_path = db.Column(db.String(200))
#     analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
#     type = db.Column(db.String(50))  # 'video', 'image', 'camera', etc.

