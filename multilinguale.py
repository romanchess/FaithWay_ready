from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
from flask_babel import Babel, gettext as _
from flask_cors import CORS
import os
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# Директория Библии
BIBLE_DIR = 'static/bible'

# Настройка Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = ['en', 'ru', 'pl']

# Создаем экземпляр Babel
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


# Главная страница
@app.route('/')
def home():
    return render_template('project.html', title=_('Faith Project'))


# Страница Библии
@app.route('/bible')
def bible():
    return render_template('bible.html', title=_('Библия'))


# Загрузка Библии по выбранному языку
@app.route('/bible/content')
def bible_content():
    lang = get_locale()
    bible_file = os.path.join(BIBLE_DIR, f'Biblia_{lang}.json')
    logging.info(f'Попытка загрузки файла: {bible_file}')

    try:
        with open(bible_file, 'r', encoding='utf-8') as f:
            bible_data = json.load(f)
        return jsonify(bible_data)
    except FileNotFoundError:
        logging.error(f'Файл не найден: {bible_file}')
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logging.error(f'Ошибка загрузки Библии: {e}')
        return jsonify({"error": "Internal server error"}), 500


# Другие страницы
@app.route('/groups')
def groups():
    return render_template('groups.html', title=_('Группы'))


@app.route('/events')
def events():
    return render_template('events.html', title=_('Мероприятия'))


@app.route('/about')
def about():
    return render_template('about.html', title=_('О нас'))


# Установка языка через cookie и редирект
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang not in app.config['LANGUAGES']:
        lang = app.config['BABEL_DEFAULT_LOCALE']

    resp = make_response(redirect(url_for(request.endpoint or 'home', lang=lang)))
    resp.set_cookie('language', lang, max_age=365 * 24 * 60 * 60)
    return resp


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
