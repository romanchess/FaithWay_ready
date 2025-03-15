from flask import Flask, render_template, redirect, url_for, request, flash, abort, jsonify, current_app
from flask_babel import _
from flask_login import login_required, current_user, login_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
import os
import json
import math

from models import db, User, Message, TestResult, Like, PrivateMessage

import logging


def load_bible_content(lang):
    bible_file = os.path.join('static', 'bible', f'Bible_{lang}.json')
    if os.path.exists(bible_file):
        with open(bible_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return None


# Checking if the file has an allowed extension by retrieving the set from the configuration

def allowed_file(filename):
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', set())
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# Fetching dating profiles with SQLAlchemy

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

    # Calculating the user's age; assuming user.dob is a date type
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


# Handling "likes" – here we use SQLAlchemy to perform a raw query

from flask import jsonify, request
from models import Like, User, PrivateMessage, db


def like_profile_func():
    data = request.get_json()
    liked_user_id = data.get('liked_user_id')

    # Checking if the user exists
    liked_user = User.query.get(liked_user_id)
    if not liked_user:
        return jsonify({'error': 'User not found'}), 404

    # Checking if a like already exists
    existing_like = Like.query.filter_by(user_id=current_user.id, liked_user_id=liked_user_id).first()

    # Checking if there is a mutual like
    reciprocal_like = Like.query.filter_by(user_id=liked_user_id, liked_user_id=current_user.id).first()

    # If the like already exists but there is no conversation yet, check the match
    if existing_like:
        if reciprocal_like:
            # Checking if there is already a conversation
            existing_message = PrivateMessage.query.filter(
                ((PrivateMessage.sender_id == current_user.id) & (PrivateMessage.receiver_id == liked_user_id)) |
                ((PrivateMessage.sender_id == liked_user_id) & (PrivateMessage.receiver_id == current_user.id))
            ).first()

            # If there is no conversation, create the first empty message (or simply allow chat)
            if not existing_message:
                first_message = PrivateMessage(
                    sender_id=current_user.id,
                    receiver_id=liked_user_id,
                    message="Chat is open! Start the conversation."
                )
                db.session.add(first_message)
                db.session.commit()

            return jsonify({'message': 'You have a match! Chat is open.', 'match': True}), 200
        else:
            return jsonify({'message': 'Like already added.', 'match': False}), 200

    # If there is no like yet, add it
    new_like = Like(user_id=current_user.id, liked_user_id=liked_user_id)
    db.session.add(new_like)
    db.session.commit()

    # If after the new like there is a mutual like, create the first message
    if reciprocal_like:
        first_message = PrivateMessage(
            sender_id=current_user.id,
            receiver_id=liked_user_id,
            message="Chat is open! Start the conversation."
        )
        db.session.add(first_message)
        db.session.commit()

        return jsonify({'message': 'You have a match! Chat is open.', 'match': True}), 200

    return jsonify({'message': 'Like successfully added.', 'match': False}), 200


def dislike_profile():
    data = request.get_json()
    user_id = data.get('user_id')
    disliked_user_id = data.get('disliked_user_id')

    if not user_id or not disliked_user_id:
        return jsonify({'error': 'Invalid data'}), 400

    # You can add a record to the database if needed
    return jsonify({'message': 'Profile disliked successfully'}), 200


def private_chat_func(user_id):
    # Checking if there is a mutual like between users
    match = Like.query.filter_by(user_id=current_user.id, liked_user_id=user_id).first() and \
            Like.query.filter_by(user_id=user_id, liked_user_id=current_user.id).first()

    if not match:
        flash("No match for chat.", "error")
        return redirect(url_for('relationship'))

    return render_template('private_chat.html', user_id=user_id)


def send_private_message_func():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message_text = data.get('message')

    if not message_text:
        return jsonify({"error": "Message cannot be empty."}), 400

    message = PrivateMessage(sender_id=current_user.id, receiver_id=receiver_id, message=message_text)
    db.session.add(message)
    db.session.commit()

    return jsonify({"status": "ok", "message": "Message sent."})


def get_private_messages_func(user_id):
    try:
        messages = PrivateMessage.query.filter(
            ((PrivateMessage.sender_id == current_user.id) & (PrivateMessage.receiver_id == user_id)) |
            ((PrivateMessage.sender_id == user_id) & (PrivateMessage.receiver_id == current_user.id))
        ).order_by(PrivateMessage.timestamp.asc()).all()

        return jsonify([
            {
                "sender": msg.sender.first_name if msg.sender else "Unknown",
                "message": msg.message,
                "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            } for msg in messages
        ])
    except Exception as e:
        print(f"Error loading messages: {e}")
        return jsonify({"error": str(e)}), 500


# Injecting configuration variables into templates

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

# Setting language

def set_language():
    lang = request.args.get("lang")
    if lang and lang in current_app.config["LANGUAGES"]:
        resp = redirect(request.referrer or url_for("home"))
        resp.set_cookie("language", lang, max_age = 60 * 60 * 24 * 30)
        return resp
    return redirect(request.referrer or url_for("home"))

# Sending messages – we create a new entry in the Message table

def send_message():
    data = request.get_json()
    text = data.get('message', '').strip()
    if text:
        new_msg = Message(user_id=current_user.id, message=text)
        db.session.add(new_msg)
        db.session.commit()
        return jsonify(status="ok", message="Message sent")
    return jsonify(status="error", message="Empty message"), 400

# Fetching messages – we sort messages in ascending order by time

def get_messages():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    results = [{
        "user": msg.user.first_name if msg.user else "Unknown",
        "message": msg.message,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for msg in messages]
    return jsonify(results)

# Updating the user's profile

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


def save_test_result():
    try:
        data = request.get_json()
        print("Raw received data:", data)

        # Extracting data from 'answers'
        answers = data.get('answers', {})
        intention = answers.get('intention')
        morality = answers.get('morality')
        marriage = answers.get('marriage')

        print(f"Intention: {intention}, Morality: {morality}, Marriage: {marriage}")

        if not intention or not morality or not marriage:
            return jsonify({"error": "All fields are required: intention, morality, marriage"}), 400

        if intention == "fun" or morality != "avoid" or marriage != "official":
            return jsonify({"message": "You are not suitable for this site."}), 400

        result = TestResult(
            user_id=current_user.id,
            intention=intention,
            morality=morality,
            marriage=marriage
        )
        db.session.add(result)
        db.session.commit()

        print("Test Result Saved Successfully")
        return jsonify({"message": "Test result saved successfully."})

    except Exception as e:
        db.session.rollback()
        print("Error saving test result:", e)
        return jsonify({"error": str(e)}), 500


    except Exception as e:
        db.session.rollback()
        print("Error saving test result:", e)
        return jsonify({"error": str(e)}), 500


def logout():
    from flask_login import logout_user
    logout_user()
    flash(_("You have been logged out"), 'info')
    return redirect(url_for('login_route'))


# User registration

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

# User login

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

# Determining the current language (for Flask-Babel)

def get_locale():
    lang = request.cookies.get("language")
    if lang and lang in current_app.config["LANGUAGES"]:
        return lang
    return request.accept_languages.best_match(current_app.config["LANGUAGES"].keys()) or current_app.config["BABEL_DEFAULT_LOCALE"]

# Auxiliary functions that we want to assign to the User model

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

# Assigning auxiliary functions to the User model
User.set_password = set_password
User.check_password = check_password
User.get_age = get_age
User.__repr__ = user_repr

# Calculating the distance between two points using the Haversine formula

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Dummy implementation – returns coordinates for a few sample cities

def get_city_coordinates(city_name):
    dummy_cities = {
        "Warsaw": (52.2297, 21.0122),
        "Krakow": (50.0647, 19.9450),
        "Moscow": (55.7558, 37.6176),
        "Lodz": (51.7592, 19.4560),
        "Wroclaw": (51.1079, 17.0385),
        "Poznan": (52.4064, 16.9252),
        "Gdansk": (54.3520, 18.6466),
        "Szczecin": (53.4285, 14.5528),
        "Bydgoszcz": (53.1235, 18.0084),
        "Lublin": (51.2465, 22.5684),
        "Katowice": (50.2649, 19.0238),
        "Bialystok": (53.1325, 23.1688),
        "Gdynia": (54.5189, 18.5305),
        "Czestochowa": (50.8118, 19.1203),
        "Radom": (51.4027, 21.1471),
        "Sosnowiec": (50.2863, 19.1041),
        "Torun": (53.0138, 18.5984),
        "Kielce": (50.8661, 20.6286),
        "Gliwice": (50.2945, 18.6714),
        "Zabrze": (50.3249, 18.7857),
        "Olsztyn": (53.7784, 20.4801),
        "Bielsko-Biala": (49.8224, 19.0469),
        "Rzeszow": (50.0413, 21.9990),
        "Ruda Slaska": (50.2599, 18.8563),
        "Rybnik": (50.0971, 18.5419),
        "Tychy": (50.1372, 18.9664),
        "Opole": (50.6751, 17.9213),
        "Gorzow Wielkopolski": (52.7368, 15.2288),
        "Elblag": (54.1522, 19.4045),
        "Plock": (52.5468, 19.7064),
        "Walbrzych": (50.7714, 16.2843),
        "Wloclawek": (52.6482, 19.0678),
        "Tarnow": (50.0138, 20.9869),
        "Chorzow": (50.2976, 18.9546),
        "Koszalin": (54.1944, 16.1722),
        "Legnica": (51.2100, 16.1619),
        "Kalisz": (51.7611, 18.0910),
        "Grudziadz": (53.4845, 18.7536),
        "Slupsk": (54.4641, 17.0287),
        "Jaworzno": (50.2051, 19.2754),
        "Jastrzebie-Zdroj": (49.9500, 18.6000),
        "Nowy Sacz": (49.6210, 20.6970),
        "Konin": (52.2230, 18.2512),
        "Piotrkow Trybunalski": (51.4056, 19.7034),
        "Inowroclaw": (52.7982, 18.2634),
        "Lubin": (51.4009, 16.2027),
        "Ostrowiec Swietokrzyski": (50.9390, 21.3850),
        "Glogow": (51.6647, 16.0845),
        "Siemianowice Slaskie": (50.3007, 19.0291),
        "Stargard": (53.3369, 15.0500),
        "Pila": (53.1510, 16.7388)
    }
    return dummy_cities.get(city_name)

# Calculating age based on a date of birth in the format 'YYYY-MM-DD'

def calculate_age(dob_str):
    birth_date = datetime.strptime(dob_str, '%Y-%m-%d')
    today = datetime.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
