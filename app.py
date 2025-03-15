from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, current_app, Response
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel, _
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from models import db, User
from functions import (
    allowed_file,
    get_dating_profiles,
    inject_conf_var,
    set_language,
    send_message,
    get_messages,
    register,
    login,
    logout,
    get_locale,
    profile_func,
    load_bible_content,
    like_profile_func,
    private_chat_func,
    send_private_message_func,
    get_private_messages_func,
    save_test_result
)
import os
import json

class Config:
    SECRET_KEY = "your_secret_key_here"
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = "ru"
    BABEL_DEFAULT_TIMEZONE = "UTC"
    LANGUAGES = {"en": "English", "ru": "Русский", "pl": "Polski"}
    UPLOAD_FOLDER = 'static/user_photos/'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

migrate = Migrate()

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate.init_app(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_route"

babel = Babel(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@babel.localeselector
def get_locale_func():
    return get_locale()

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    return profile_func()

@app.context_processor
def inject_conf():
    return inject_conf_var()

@app.route("/")
def home():
    return render_template("project.html", title="Главная")

@app.route("/bible")
def bible():
    return render_template("bible.html", title="Библия")


@app.route('/bible/content')
def bible_content():
    lang = request.args.get('lang', 'ru')
    content = load_bible_content(lang)

    if content:
        # Возвращаем JSON без экранирования кириллицы
        return Response(
            json.dumps(content, ensure_ascii=False),
            content_type='application/json; charset=utf-8'
        )
    else:
        return jsonify({"error": "Файл не найден"}), 404

@app.route("/groups")
def groups():
    return render_template("groups.html", title="Группы")

@app.route("/groups/chat")
def chat():
    return render_template("chat.html", user=current_user)

@app.route("/events")
def events():
    return render_template("events.html", title="Мероприятия")

@app.route("/about")
def about():
    return render_template("about.html", title="О нас")

@app.route("/groups/fellowship")
@login_required
def fellowship():
    return render_template("fellowship.html", title="Дружба и поддержка")

@app.route("/groups/relationship")
@login_required
def relationship():
    profile = current_user
    return render_template("relationship.html", title="Знакомства в вере", profile=profile)

@app.route("/set_language")
def language():
    return set_language()

@app.route("/register", methods=["GET", "POST"])
def register_route():
    return register()

@app.route("/login", methods=["GET", "POST"])
def login_route():
    return login()

@app.route("/logout")
@login_required
def logout_route():
    return logout()

@app.route('/save_test_result', methods=['POST'])
@login_required
def save_test_result_route():
    return save_test_result()



@app.route("/send_message", methods=["POST"])
@login_required
def send_message_route():
    return send_message()

@app.route("/get_messages", methods=["GET"])
@login_required
def get_messages_route():
    return get_messages()

@app.route("/get_dating_profiles", methods=["GET"])
def dating_profiles():
    return get_dating_profiles()

@app.route("/like_profile", methods=["POST"])
def like_profile_route():
    return like_profile_func()

@app.route('/private_chat/<int:user_id>')
@login_required
def private_chat(user_id):
       return render_template('private_chat.html', user_id=user_id)

@app.route("/send_private_message", methods=["POST"])
@login_required
def send_private_message():
    return send_private_message_func()

@app.route('/get_private_messages/<int:user_id>')
@login_required
def get_private_messages(user_id):
    return get_private_messages_func(user_id)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)