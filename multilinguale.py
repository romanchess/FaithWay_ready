from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
import os

# Импортируем объекты базы данных и модели
from models import db, User, Message

class Config:
    SECRET_KEY = "your_secret_key_here"  # ключ для сессий и CSRF-защиты
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"  # строка подключения к базе данных
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = "ru"
    BABEL_DEFAULT_TIMEZONE = "UTC"
    LANGUAGES = {
        "en": "English",
        "ru": "Русский",
        "pl": "Polski"
    }

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # если пользователь не авторизован, перебросит на 'auth.login'

babel = Babel(app)

# Папка для загрузки фото профиля
UPLOAD_FOLDER = 'static/user_photos/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Проверяем, разрешён ли формат файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Flask-Login: подгружаем пользователя по ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Определяем локаль (Flask-Babel)
@babel.localeselector
def get_locale():
    lang = request.cookies.get("language")
    if lang and lang in app.config["LANGUAGES"]:
        return lang
    return request.accept_languages.best_match(app.config["LANGUAGES"].keys()) \
           or app.config["BABEL_DEFAULT_LOCALE"]

@app.context_processor
def inject_conf_var():
    selected_lang = request.cookies.get("language")
    if not selected_lang:
        selected_lang = request.accept_languages.best_match(app.config["LANGUAGES"].keys())
    if not selected_lang:
        selected_lang = app.config["BABEL_DEFAULT_LOCALE"]
    return {
        "AVAILABLE_LANGUAGES": app.config["LANGUAGES"],
        "CURRENT_LANGUAGE": selected_lang,
        "get_locale": get_locale
    }

# ---------- Основные маршруты ----------
@app.route("/")
def home():
    return render_template("project.html", title="Главная")

@app.route("/bible")
def bible():
    return render_template("bible.html", title="Библия")

@app.route("/groups")
def groups():
    """
    Страница 'Группы' (главная страница раздела).
    Здесь можно сделать три ссылки:
    1) Общий чат: /groups/chat
    2) Общение и поиск единомышленников
    3) Поиск знакомств и любви
    """
    return render_template("groups.html", title="Группы")

@app.route("/groups/chat")
@login_required
def chat():
    """
    Общий чат (требует авторизации).
    Показывает шаблон chat.html, где размещён JS для чата.
    """
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
    return render_template("relationship.html", title="Знакомства в вере")


@app.route("/set_language")
def set_language():
    """Маршрут для смены языка приложения"""
    lang = request.args.get("lang")
    if lang and lang in app.config["LANGUAGES"]:
        resp = redirect(request.referrer or url_for("home"))
        resp.set_cookie("language", lang, max_age = 60 * 60 * 24 * 30)
        return resp
    return redirect(request.referrer or url_for("home"))

# ---------- Маршруты для чата ----------
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    """
    Принимает JSON: { "message": "Текст" }
    Сохраняет сообщение в БД, возвращает JSON-ответ.
    """
    data = request.get_json()
    text = data.get('message', '').strip()
    if text:
        new_msg = Message(user_id=current_user.id, message=text)
        db.session.add(new_msg)
        db.session.commit()
        return jsonify(status="ok", message="Message sent")
    return jsonify(status="error", message="Empty message"), 400

@app.route('/get_messages', methods=['GET'])
@login_required
def get_messages():
    """
    Возвращает список всех сообщений в формате JSON.
    """
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    results = [{
        "user": msg.user.first_name if msg.user else "Unknown",
        "message": msg.message,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for msg in messages]
    return jsonify(results)

# ---------- Маршрут профиля ----------
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.city = request.form.get('city')
        current_user.bio = request.form.get('bio')
        # Загрузка фото
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.profile_picture = filename
        db.session.commit()
        flash("Profile updated successfully!", 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

# ---------- Подключение blueprint-а аутентификации ----------
from auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint)

# ---------- Создание БД и запуск ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
