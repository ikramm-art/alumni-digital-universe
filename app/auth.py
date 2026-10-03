import re
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from . import db
from .models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _profile_redirect():
    return redirect(url_for("main.profile"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _profile_redirect()

    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")

        if not name or len(name) > 120:
            flash("Enter a name between 1 and 120 characters.", "error")
            return redirect(url_for("auth.register"))
        if len(email) > 160 or not EMAIL_PATTERN.fullmatch(email):
            flash("Enter a valid email address.", "error")
            return redirect(url_for("auth.register"))
        if len(password) < 8 or len(password) > 128:
            flash("Password must be between 8 and 128 characters.", "error")
            return redirect(url_for("auth.register"))
        if password != confirmation:
            flash("Password confirmation does not match.", "error")
            return redirect(url_for("auth.register"))
        graduation_year_raw = request.form.get("graduation_year", "").strip()
        graduation_year = None
        if graduation_year_raw:
            try:
                graduation_year = int(graduation_year_raw)
            except ValueError:
                flash("Enter a valid graduation year.", "error")
                return redirect(url_for("auth.register"))
            if not 1900 <= graduation_year <= 2100:
                flash("Graduation year must be between 1900 and 2100.", "error")
                return redirect(url_for("auth.register"))

        if len(request.form.get("class_name", "").strip()) > 80:
            flash("Class must be 80 characters or fewer.", "error")
            return redirect(url_for("auth.register"))
        if len(request.form.get("generation", "").strip()) > 80:
            flash("Generation must be 80 characters or fewer.", "error")
            return redirect(url_for("auth.register"))
        if User.query.filter(db.func.lower(User.email) == email).first():
            flash("An account with that email already exists.", "error")
            return redirect(url_for("auth.register"))

        user = User(
            email=email,
            full_name=name,
            class_name=request.form.get("class_name", "").strip() or None,
            generation=request.form.get("generation", "").strip() or None,
            graduation_year=graduation_year,
        )
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with that email already exists.", "error")
            return redirect(url_for("auth.register"))

        login_user(user)
        flash("Your account is ready. Welcome to the Alumni Universe.", "success")
        return _profile_redirect()

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _profile_redirect()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter(db.func.lower(User.email) == email).first() if email else None

        if not user or not password or not user.check_password(password):
            flash("Email or password is incorrect.", "error")
            return redirect(url_for("auth.login"))

        login_user(user)
        flash("Welcome back.", "success")
        return _profile_redirect()

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))
