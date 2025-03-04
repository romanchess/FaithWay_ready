from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import gettext as _
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, User

auth = Blueprint('auth', __name__, template_folder='templates')


@auth.route('/register', methods=['GET', 'POST'])
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

        # Basic validation checks
        if not first_name or not last_name:
            errors.append(_("First name and last name are required"))
        if password != confirm_password:
            errors.append(_("Passwords do not match"))
        if len(password) < 8:
            errors.append(_("Password must be at least 8 characters long"))
        if not (email or phone):
            errors.append(_("Please provide either an email or a phone number"))

        # Check for existing user with the same email or phone number
        existing_user = User.query.filter((User.email == email) | (User.phone == phone)).first()
        if existing_user:
            errors.append(_("This email or phone number is already in use"))

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', title=_("Registration"))

        # Create a new user instance
        user = User(first_name=first_name, last_name=last_name, email=email, phone=phone, gender=gender)

        # Convert date of birth from string to date format
        if dob:
            from datetime import datetime
            try:
                user.dob = datetime.strptime(dob, "%Y-%m-%d").date()
            except Exception:
                flash(_("Invalid date format"), 'error')
                return render_template('register.html', title=_("Registration"))

        # Hash the password before storing it in the database
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


@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect authenticated users to the home page
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone')
        password = request.form.get('password')

        # Find the user by email or phone
        user = User.query.filter((User.email == email_or_phone) | (User.phone == email_or_phone)).first()

        # Verify password and log the user in
        if user and user.check_password(password):
            login_user(user)
            flash(_("Login successful"), 'success')
            return redirect(url_for('home'))
        else:
            flash(_("Invalid login credentials"), 'error')

    return render_template('login.html', title=_("Login"))


@auth.route('/logout')
@login_required
def logout():
    # Log the user out and redirect to login page
    logout_user()
    flash(_("You have been logged out"), 'info')
    return redirect(url_for('auth.login'))
