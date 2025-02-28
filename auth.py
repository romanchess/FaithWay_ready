from flask import Blueprint, request, jsonify
import re

auth = Blueprint("auth", __name__)

# Фейковая база пользователей (замените на БД в будущем)
users = []

# Проверка пароля
def validate_password(password, confirm_password):
    if len(password) < 8:
        return "Пароль должен быть минимум 8 символов"
    if password != confirm_password:
        return "Пароли не совпадают"
    return None

# Проверка email/телефона
def validate_contact(contact):
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    phone_regex = r"^\+?\d{7,15}$"

    if not re.match(email_regex, contact) and not re.match(phone_regex, contact):
        return "Введите корректную почту или телефон"
    return None

# Роут для регистрации
@auth.route("/register", methods=["POST"])
def register():
    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    contact = data.get("contact")
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    gender = data.get("gender")
    birth_date = data.get("birth_date")

    # Проверка данных
    error = validate_password(password, confirm_password) or validate_contact(contact)
    if error:
        return jsonify({"error": error}), 400

    users.append({
        "first_name": first_name,
        "last_name": last_name,
        "contact": contact,
        "password": password,  # В реальности нужно хешировать
        "gender": gender,
        "birth_date": birth_date
    })

    return jsonify({"message": "Регистрация успешна!"})
