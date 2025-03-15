import requests
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
from datetime import datetime


# Inicjalizacja bazy danych
db = SQLAlchemy()

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Odniesienie do tabeli 'user'
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Relacja z modelem User – dzięki temu możemy łatwo pobierać informacje o użytkowniku, który wysłał wiadomość
    user = db.relationship('User', backref=db.backref('messages', lazy=True))

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    gender = db.Column(db.String(20))
    dob = db.Column(db.Date)
    city = db.Column(db.String(128))       # Miasto użytkownika
    bio = db.Column(db.Text)                # Krótkie o sobie
    profile_picture = db.Column(db.String(256), default='default.jpg')  # Zdjęcie profilowe
    created_at = db.Column(db.DateTime, default=date.today)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    liked_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  # Użytkownik, który został polubiony

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    intention = db.Column(db.String(100), nullable=False)
    morality = db.Column(db.String(100), nullable=False)
    marriage = db.Column(db.String(100), nullable=False)


class PrivateMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')


