from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify, current_app
from flask_babel import _
from flask_login import login_required, current_user, login_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
import os
import math

from models import db, User, Message

# Sprawdzenie, czy plik ma dozwolone rozszerzenie, pobierając zestaw z konfiguracji
def allowed_file(filename):
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', set())
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# Pobieranie profili randkowych z wykorzystaniem SQLAlchemy
def get_dating_profiles():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_coords = get_city_coordinates(user.city)
    if not user_coords:
        return jsonify({"error": "City coordinates not found"}), 404

    # Obliczamy wiek użytkownika; zakładamy, że user.dob jest typu date
    user_age = calculate_age(user.dob.strftime('%Y-%m-%d')) if user.dob else None
    opposite_gender = 'male' if user.gender == 'female' else 'female'
    candidates = User.query.filter_by(gender=opposite_gender).all()
    result = []
    for candidate in candidates:
        coords = get_city_coordinates(candidate.city)
        if coords and user_age is not None and candidate.dob:
            distance = haversine(user_coords[0], user_coords[1], coords[0], coords[1])
            candidate_age = calculate_age(candidate.dob.strftime('%Y-%m-%d'))
            if abs(user_age - candidate_age) <= 7 and distance <= 50:
                result.append({
                    "id": candidate.id,
                    "name": f"{candidate.first_name} {candidate.last_name}",
                    "city": candidate.city,
                    "age": candidate_age,
                    "distance_km": round(distance, 2),
                    "profile_picture": candidate.profile_picture
                })
    result.sort(key=lambda x: x['distance_km'])
    return jsonify(result)

# Obsługa "lajków" – tutaj wykorzystujemy SQLAlchemy do wykonania surowego zapytania
def like_profile():
    data = request.get_json()
    user_id = data.get('user_id')
    liked_user_id = data.get('liked_user_id')
    if not user_id or not liked_user_id:
        return jsonify({"error": "User IDs required"}), 400
    try:
        query = "INSERT INTO likes (user_id, liked_user_id) VALUES (:user_id, :liked_user_id)"
        db.engine.execute(query, user_id=user_id, liked_user_id=liked_user_id)
        query2 = "SELECT id FROM likes WHERE user_id = :liked_user_id AND liked_user_id = :user_id"
        match = db.engine.execute(query2, liked_user_id=liked_user_id, user_id=user_id).fetchone()
        if match:
            return jsonify({"match": True, "message": "У вас совпадение! Теперь вы можете общаться."})
        else:
            return jsonify({"match": False, "message": "Лайк отправлен."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Wstrzykiwanie zmiennych konfiguracyjnych do szablonów
def inject_conf_var():
    selected_lang = request.cookies.get("language")
    if not selected_lang:
        selected_lang = request.accept_languages.best_match(current_app.config["LANGUAGES"].keys())
    if not selected_lang:
        selected_lang = current_app.config["BABEL_DEFAULT_LOCALE"]
    return {
        "AVAILABLE_LANGUAGES": current_app.config["LANGUAGES"],
        "CURRENT_LANGUAGE": selected_lang,
        "get_locale": get_locale
    }

# Ustawianie języka
def set_language():
    lang = request.args.get("lang")
    if lang and lang in current_app.config["LANGUAGES"]:
        resp = redirect(request.referrer or url_for("home"))
        resp.set_cookie("language", lang, max_age = 60 * 60 * 24 * 30)
        return resp
    return redirect(request.referrer or url_for("home"))

# Wysyłanie wiadomości – tworzymy nowy wpis w tabeli Message
def send_message():
    data = request.get_json()
    text = data.get('message', '').strip()
    if text:
        new_msg = Message(user_id=current_user.id, message=text)
        db.session.add(new_msg)
        db.session.commit()
        return jsonify(status="ok", message="Message sent")
    return jsonify(status="error", message="Empty message"), 400

# Pobieranie wiadomości – sortujemy wiadomości rosnąco według czasu
def get_messages():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    results = [{
        "user": msg.user.first_name if msg.user else "Unknown",
        "message": msg.message,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for msg in messages]
    return jsonify(results)

# Aktualizacja profilu użytkownika
def profile_func():
    if request.method == 'POST':
        current_user.city = request.form.get('city')
        current_user.bio = request.form.get('bio')
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                current_user.profile_picture = filename
        db.session.commit()
        flash("Profile updated successfully!", 'success')
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

def logout():
    from flask_login import logout_user
    logout_user()
    flash(_("You have been logged out"), 'info')
    return redirect(url_for('login'))


# Rejestracja użytkownika
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        dob = request.form.get('dob')
        errors = []
        if not first_name or not last_name:
            errors.append(_("First name and last name are required"))
        if password != confirm_password:
            errors.append(_("Passwords do not match"))
        if len(password) < 8:
            errors.append(_("Password must be at least 8 characters long"))
        if not (email or phone):
            errors.append(_("Please provide either an email or a phone number"))
        existing_user = User.query.filter((User.email == email) | (User.phone == phone)).first()
        if existing_user:
            errors.append(_("This email or phone number is already in use"))
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', title=_("Registration"))
        user = User(first_name=first_name, last_name=last_name, email=email, phone=phone, gender=gender)
        if dob:
            try:
                user.dob = datetime.strptime(dob, "%Y-%m-%d").date()
            except Exception:
                flash(_("Invalid date format"), 'error')
                return render_template('register.html', title=_("Registration"))
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
            flash(_("Registration successful! You can now log in."), 'success')
            return redirect(url_for('auth.login'))
        except IntegrityError:
            db.session.rollback()
            flash(_("This email or phone number is already registered"), 'error')
        except Exception as e:
            db.session.rollback()
            flash(_("Database error: ") + str(e), 'error')
    return render_template('register.html', title=_("Registration"))

# Logowanie użytkownika
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone')
        password = request.form.get('password')
        user = User.query.filter((User.email == email_or_phone) | (User.phone == email_or_phone)).first()
        if user and user.check_password(password):
            login_user(user)
            flash(_("Login successful"), 'success')
            return redirect(url_for('home'))
        else:
            flash(_("Invalid login credentials"), 'error')
    return render_template('login.html', title=_("Login"))

# Określanie aktualnego języka (dla Flask-Babel)
def get_locale():
    lang = request.cookies.get("language")
    if lang and lang in current_app.config["LANGUAGES"]:
        return lang
    return request.accept_languages.best_match(current_app.config["LANGUAGES"].keys()) or current_app.config["BABEL_DEFAULT_LOCALE"]

# Funkcje pomocnicze, które chcemy przypisać do modelu User
def set_password(self, password):
    from werkzeug.security import generate_password_hash
    self.password_hash = generate_password_hash(password)

def check_password(self, password):
    from werkzeug.security import check_password_hash
    return check_password_hash(self.password_hash, password)

def get_age(self):
    if self.dob:
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
    return None

def user_repr(self):
    return f'<User {self.first_name} {self.last_name}>'

# Przypisanie funkcji pomocniczych do modelu User
User.set_password = set_password
User.check_password = check_password
User.get_age = get_age
User.__repr__ = user_repr

# Funkcja obliczająca odległość między dwoma punktami przy użyciu formuły Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Promień Ziemi w km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Dummy implementation – zwraca współrzędne dla kilku przykładowych miast
def get_city_coordinates(city_name):
    dummy_cities = {
        "Warsaw": (52.2297, 21.0122),
        "Krakow": (50.0647, 19.9450),
        "Moscow": (55.7558, 37.6176)
    }
    return dummy_cities.get(city_name)

# Funkcja obliczająca wiek na podstawie daty urodzenia w formacie 'YYYY-MM-DD'
def calculate_age(dob_str):
    birth_date = datetime.strptime(dob_str, '%Y-%m-%d')
    today = datetime.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
