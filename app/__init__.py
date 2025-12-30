from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

from werkzeug.security import generate_password_hash
from app.models import User
from app import db

def create_admin_user():
    admin_email = "contact@multticonstruction.com"
    admin_password = "Africa19!"

    user = User.query.filter_by(email=admin_email).first()

    if user:
        # ✅ User exists → ensure admin role
        if user.role != "admin":
            user.role = "admin"
            db.session.commit()
            print("🔁 Existing user promoted to admin.")
        else:
            print("ℹ️ Admin user already exists.")
    else:
        # ✅ User does not exist → create admin
        admin = User(
            full_name="Admin",
            address="Admin Address",
            phone="0000000000",
            email=admin_email,
            password=generate_password_hash(admin_password),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin user created.")


def create_app():
    app = Flask(__name__)

    # ✅ Load config (make sure your environment sets this correctly)
    app.config.from_object("config.Config")

    # ✅ Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ✅ Register blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # ✅ Create DB tables and seed admin
    with app.app_context():
        db.create_all()
        create_admin_user()

    return app
