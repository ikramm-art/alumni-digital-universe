from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="alumni", server_default=db.text("'alumni'"))
    class_name = db.Column(db.String(80))
    generation = db.Column(db.String(80))
    entry_year = db.Column(db.Integer)
    graduation_year = db.Column(db.Integer)
    bio = db.Column(db.Text)
    city = db.Column(db.String(100))
    occupation = db.Column(db.String(120))
    university = db.Column(db.String(160))
    major = db.Column(db.String(160))
    university_year = db.Column(db.Integer)
    instagram = db.Column(db.String(255))
    github = db.Column(db.String(255))
    linkedin = db.Column(db.String(255))
    profile_photo = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memories = db.relationship("Memory", backref="uploader", lazy=True, cascade="all, delete-orphan")
    highlights = db.relationship("Highlight", backref="owner", lazy=True, cascade="all, delete-orphan")

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Highlight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    year = db.Column(db.Integer)
    location = db.Column(db.String(160))
    category = db.Column(db.String(80), default="Other")
    image = db.Column(db.String(255))
    status = db.Column(db.String(30), default="approved")
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Timeline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    location = db.Column(db.String(160))


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
