import os
import secrets
from flask import Flask
import click
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect


db = SQLAlchemy()
login_manager = LoginManager()


def ensure_user_role_column(engine):
    """Add the role column to legacy databases without changing existing rows."""
    inspector = inspect(engine)
    if not inspector.has_table("user"):
        return
    columns = {column["name"] for column in inspector.get_columns("user")}
    if "role" in columns:
        return

    quoted_table = engine.dialect.identifier_preparer.quote("user")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"ALTER TABLE {quoted_table} "
            "ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'alumni'"
        )


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///alumni.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join(app.instance_path, "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from .models import User
    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.cli.command("promote-admin")
    @click.argument("email")
    def promote_admin_command(email):
        """Promote an existing account after showing its identity for confirmation."""
        from .auth import EMAIL_PATTERN

        normalized_email = email.strip().lower()
        if len(normalized_email) > 160 or not EMAIL_PATTERN.fullmatch(normalized_email):
            raise click.ClickException("Provide a valid existing account email.")

        account = User.query.filter(db.func.lower(User.email) == normalized_email).first()
        if account is None:
            raise click.ClickException("No existing account matches that email; no account was created.")

        click.echo(f"Existing account: {account.full_name} <{account.email}> · role: {account.role}")
        if account.is_admin:
            click.echo("This account is already an admin; no changes made.")
            return
        if not click.confirm("Promote this existing account to ADMIN?", default=False):
            click.echo("Cancelled; account unchanged.")
            return

        account.role = "admin"
        db.session.commit()
        click.echo("Existing account promoted to ADMIN.")
    # Preserve the existing /auth/login URL while also supporting the requested /login path.
    app.add_url_rule(
        "/login",
        endpoint="login_alias",
        view_func=app.view_functions["auth.login"],
        methods=["GET", "POST"],
    )

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    with app.app_context():
        db.create_all()
        ensure_user_role_column(db.engine)

    return app
