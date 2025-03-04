from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from flask_login import LoginManager, login_required, current_user
# Импортируем общие объекты базы данных и модели пользователя
from models import db, User

# Глобальная конфигурация приложения
class Config:
    SECRET_KEY = "your_secret_key_here"  # ключ для сессий и CSRF-защиты
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"  # строка подключения к базе данных
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = "ru"       # язык по умолчанию
    BABEL_DEFAULT_TIMEZONE = "UTC"
    LANGUAGES = {
        "en": "English",
        "ru": "Русский",
        "es": "Español"
    }

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация базы данных (SQLAlchemy) с приложением
db.init_app(app)

# Настройка Flask-Login (LoginManager)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # страница входа для неавторизованных (маршрут auth.login)

# Инициализация Flask-Babel для мультиязычности
babel = Babel(app)

# Функция загрузки пользователя по ID (для Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Выбор текущей локали для перевода (Flask-Babel)
@babel.localeselector
def get_locale():
    # Если пользователь выбрал язык (есть cookie), используем его
    lang = request.cookies.get("language")
    if lang and lang in app.config["LANGUAGES"]:
        return lang
    # Иначе берём лучший язык из заголовков браузера или используем язык по умолчанию
    return request.accept_languages.best_match(app.config["LANGUAGES"].keys()) or app.config["BABEL_DEFAULT_LOCALE"]

# Делаем доступными некоторые параметры в шаблонах (например, список языков)
@app.context_processor
def inject_conf_var():
    selected_lang = request.cookies.get("language")
    if not selected_lang:
        selected_lang = request.accept_languages.best_match(app.config["LANGUAGES"].keys())
    if not selected_lang:
        selected_lang = app.config["BABEL_DEFAULT_LOCALE"]
    return dict(
        AVAILABLE_LANGUAGES=app.config["LANGUAGES"],
        CURRENT_LANGUAGE=selected_lang,
        get_locale=get_locale  # функция выбора локали доступна в шаблонах
    )

# Маршруты приложения (основные страницы)
@app.route("/")
def home():
    return render_template("project.html", title="Главная")

@app.route("/bible")
def bible():
    return render_template("bible.html", title="Библия")

@app.route("/groups")
def groups():
    return render_template("groups.html", title="Группы")

@app.route("/events")
def events():
    return render_template("events.html", title="Мероприятия")

@app.route("/about")
def about():
    return render_template("about.html", title="О нас")

@app.route("/set_language")
def set_language():
    # Маршрут для смены языка приложения
    lang = request.args.get("lang")
    if lang and lang in app.config["LANGUAGES"]:
        # Устанавливаем cookie с выбранным языком на 30 дней
        resp = redirect(request.referrer or url_for("home"))
        resp.set_cookie("language", lang, max_age=60*60*24*30)
        return resp
    # Если язык не поддерживается или не передан, перенаправляем назад
    return redirect(request.referrer or url_for("home"))

@app.route("/profile")
@login_required
def profile():
    # Профиль (только для авторизованных пользователей)
    return render_template("profile.html", title="Профиль", user=current_user)

# Подключение маршрутов аутентификации из blueprint 'auth'
from auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint)

# Создание базы данных при запуске приложения
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # создаём таблицы в базе (если ещё не существуют)
    app.run(debug=True)
