from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
from flask_babel import Babel, gettext as _
from flask_cors import CORS
from flask_login import LoginManager  # ✅ Добавляем Flask-Login
import os
import json
import logging

# Import database and models
from models import db, User  # ✅ Добавляем User, чтобы Flask-Login знал модель пользователя
# Import authentication blueprint
from auth import auth as auth_blueprint

# Настройка логирования
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///faith_project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # ✅ Нужен для Flask-Login (сессий)
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()  # ✅ Создаем менеджер входа
login_manager.init_app(app)  # ✅ Подключаем его к приложению
login_manager.login_view = 'auth.login'  # ✅ Указываем страницу логина

# Функция для загрузки пользователя по ID (обязательна для Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register authentication blueprint
app.register_blueprint(auth_blueprint)

# Directory for Bible files
BIBLE_DIR = 'static/bible'

# Babel configuration
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = ['en', 'ru', 'pl']

babel = Babel(app)

@babel.localeselector
def get_locale():
    lang = request.args.get('lang')
    if lang in app.config['LANGUAGES']:
        return lang
    cookie_lang = request.cookies.get('language')
    if cookie_lang in app.config['LANGUAGES']:
        return cookie_lang
    return request.accept_languages.best_match(app.config['LANGUAGES']) or app.config['BABEL_DEFAULT_LOCALE']

@app.context_processor
def inject_locale():
    return {'get_locale': get_locale}

# Home page
@app.route('/')
def home():
    return render_template('project.html', title=_('Faith Project'))

# Bible page
@app.route('/bible')
def bible():
    return render_template('bible.html', title=_('Библия'))

# Load Bible content by selected language
@app.route('/bible/content')
def bible_content():
    lang = get_locale()
    bible_file = os.path.join(BIBLE_DIR, f'Biblia_{lang}.json')
    logging.info(f'Attempting to load file: {bible_file}')
    try:
        with open(bible_file, 'r', encoding='utf-8') as f:
            bible_data = json.load(f)
        return jsonify(bible_data)
    except FileNotFoundError:
        logging.error(f'File not found: {bible_file}')
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logging.error(f'Error loading Bible: {e}')
        return jsonify({"error": "Internal server error"}), 500

# Other pages
@app.route('/groups')
def groups():
    return render_template('groups.html', title=_('Группы'))

@app.route('/events')
def events():
    return render_template('events.html', title=_('Мероприятия'))

@app.route('/about')
def about():
    return render_template('about.html', title=_('О нас'))

# Set language via cookie and redirect to home page
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang not in app.config['LANGUAGES']:
        lang = app.config['BABEL_DEFAULT_LOCALE']
    resp = make_response(redirect(url_for('home', lang=lang)))
    resp.set_cookie('language', lang, max_age=365 * 24 * 60 * 60)
    return resp

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)  # ✅ Включаем debug для тестирования
