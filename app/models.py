from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import JSON

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')  # 'admin' or 'customer'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


from sqlalchemy import JSON  # already imported

class EstimateRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    estimate_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_type = db.Column(db.String(50), nullable=False)
    services = db.Column(db.Text, nullable=False)
    total_sqft = db.Column(db.Integer)
    details = db.Column(db.Text)
    sketch_filename = db.Column(db.String(100))  # Optional: keep one for compatibility
    image_filenames = db.Column(db.Text)  # ✅ NEW: stores comma-separated image names
    status = db.Column(db.String(30), default='Waiting Estimate')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    estimate_pdf = db.Column(db.String(100))
    customer_response = db.Column(db.String(20))


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_number = db.Column(db.String(20), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer = db.relationship('User', backref='projects')
    project_type = db.Column(db.String(50), nullable=False)
    services = db.Column(db.Text, nullable=False)
    total_sqft = db.Column(db.Integer)
    details = db.Column(db.Text)
    sketch_filename = db.Column(db.String(100))
    status = db.Column(db.String(30), default='Pending Schedule')  # or Schedule Approved, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    schedule_data = db.Column(JSON, nullable=True)
    messages = db.relationship('ProjectMessage', backref='project', lazy=True, cascade='all, delete-orphan')
    uploads = db.relationship('ProjectUpload', backref='project', lazy=True, cascade='all, delete-orphan')

class ProjectMessage(db.Model):
    __tablename__ = 'project_messages'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    sender = db.Column(db.String(50))  # 'customer' or 'admin'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ProjectUpload(db.Model):
    __tablename__ = 'project_uploads'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)