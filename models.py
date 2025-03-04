from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime

# Инициализация базы данных


db = SQLAlchemy()

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # связь с таблицей пользователей
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Опционально: определяем отношение к модели User, если она есть
    user = db.relationship('User', backref=db.backref('messages', lazy=True))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    gender = db.Column(db.String(20))
    dob = db.Column(db.Date)
    city = db.Column(db.String(128))  # Новый параметр: Город
    bio = db.Column(db.Text)  # Новый параметр: Краткое описание о себе
    profile_picture = db.Column(db.String(256), default='default.jpg')  # Фото профиля
    created_at = db.Column(db.DateTime, default=date.today)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_age(self):
        if self.dob:
            today = date.today()
            age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
            return age
        return None



    def __repr__(self):
        return f'<User {self.first_name} {self.last_name}>'
