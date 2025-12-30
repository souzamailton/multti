from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import db
from app.forms import (
    RegisterForm,
    LoginForm,
    EstimateRequestForm,
    AdminEstimateUploadForm,
    SERVICES
)
from app.models import User, EstimateRequest, Project
import uuid, os
from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField
from wtforms.validators import Optional
from flask import request
from app.models import Project, ProjectMessage, ProjectUpload


bp = Blueprint('main', __name__)

# ------------------ AUTH ------------------

@bp.route('/')
def index():
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.')
            return redirect(url_for('main.register'))

        user = User(
            full_name=form.full_name.data,
            address=form.address.data,
            phone=form.phone.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            role='customer'
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(
                url_for('main.admin_dashboard')
                if user.role == 'admin'
                else url_for('main.customer_dashboard')
            )
        flash('Invalid email or password.')

    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# ------------------ CUSTOMER ------------------

@bp.route('/dashboard')
@login_required
def customer_dashboard():
    if current_user.role != 'customer':
        return redirect(url_for('main.admin_dashboard'))

    # Get all estimates for display
    estimates = EstimateRequest.query.filter_by(customer_id=current_user.id).order_by(EstimateRequest.timestamp.desc()).all()

    # Also get active projects
    projects = Project.query.filter_by(customer_id=current_user.id).order_by(Project.created_at.desc()).all()

    return render_template('customer_dashboard.html', estimates=estimates, projects=projects)

@bp.route('/request-estimate', methods=['GET', 'POST'])
@login_required
def request_estimate():
    form = EstimateRequestForm()
    form.services.choices = [(s, s) for s in SERVICES.get(form.project_type.data, [])]

    if form.validate_on_submit():
        estimate_number = f"EST-{uuid.uuid4().hex[:8].upper()}"

        image_filenames = []

        # Handle multiple image uploads (up to 5)
        if form.images.data:
            upload_path = os.path.join(current_app.root_path, 'static/uploads')
            os.makedirs(upload_path, exist_ok=True)

            for file in form.images.data[:5]:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(upload_path, filename))
                    image_filenames.append(filename)

        # Backward compatibility (optional)
        sketch_filename = image_filenames[0] if image_filenames else None

        estimate = EstimateRequest(
            estimate_number=estimate_number,
            customer_id=current_user.id,
            project_type=form.project_type.data,
            services=",".join(request.form.getlist('services')),
            total_sqft=form.total_sqft.data,
            details=form.details.data,
            sketch_filename=sketch_filename,
            image_filenames=",".join(image_filenames)  # ✅ THIS WAS MISSING
        )

        db.session.add(estimate)
        db.session.commit()

        flash("Estimate request submitted.")
        return redirect(url_for('main.customer_dashboard'))

    return render_template('request_estimate.html', form=form, services_json=SERVICES)


@bp.route('/track-projects')
@login_required
def track_projects():
    if current_user.role != 'customer':
        return redirect(url_for('main.admin_dashboard'))

    in_progress = Project.query.filter_by(customer_id=current_user.id).filter(
        Project.status.in_(['Pending Schedule', 'Schedule Approved'])
    ).all()

    completed = Project.query.filter_by(customer_id=current_user.id, status='Completed').all()

    return render_template(
        'track_projects.html',
        in_progress=in_progress,
        completed=completed
    )

# ------------------ ADMIN ------------------

@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('main.customer_dashboard'))

    # Get all in-progress projects
    in_progress_projects = Project.query.filter(
        Project.status.in_([
            'Pending Schedule',
            'Waiting for Schedule Approval',
            'Schedule Approved'
        ])
    ).all()

    # ✅ Get all estimate requests, ordered by newest first
    estimate_requests = EstimateRequest.query.order_by(EstimateRequest.timestamp.desc()).all()

    return render_template(
        'admin_dashboard.html',
        in_progress_projects=in_progress_projects,
        estimate_requests=estimate_requests
    )

@bp.route('/admin/estimate-requests')
@login_required
def admin_estimate_requests():
    if current_user.role != 'admin':
        return redirect(url_for('main.customer_dashboard'))

    pending = EstimateRequest.query.filter_by(status='Waiting Estimate').all()
    return render_template('admin_estimate_requests.html', pending=pending)


# ✅ SINGLE, CORRECT ADMIN VIEW (NO DUPLICATES)
@bp.route('/admin/estimate/<int:estimate_id>/view', methods=['GET', 'POST'])
@login_required
def admin_view_estimate_request(estimate_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.customer_dashboard'))

    estimate = EstimateRequest.query.get_or_404(estimate_id)
    customer = User.query.get(estimate.customer_id)
    form = AdminEstimateUploadForm()

    if form.validate_on_submit():
        upload_path = os.path.join(current_app.root_path, 'static/estimates')
        os.makedirs(upload_path, exist_ok=True)

        filename = f"{estimate.estimate_number}_{secure_filename(form.estimate_pdf.data.filename)}"
        form.estimate_pdf.data.save(os.path.join(upload_path, filename))

        estimate.estimate_pdf = filename
        estimate.status = 'Estimate Received'
        db.session.commit()

        flash("Estimate uploaded and sent to customer.")
        return redirect(url_for('main.admin_estimate_requests'))

    return render_template(
        'view_estimate_request.html',
        estimate=estimate,
        customer=customer,
        form=form
    )

# ------------------ CUSTOMER APPROVAL ------------------

@bp.route('/estimate/<int:estimate_id>/approve')
@login_required
def approve_estimate(estimate_id):
    estimate = EstimateRequest.query.get_or_404(estimate_id)

    if estimate.customer_id != current_user.id:
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    # Update estimate status
    estimate.status = 'Estimate Approved'
    estimate.customer_response = 'Approved'

    # ✅ Check if project already exists
    existing_project = Project.query.filter_by(project_number=estimate.estimate_number).first()

    if not existing_project:
        project = Project(
            project_number=estimate.estimate_number,
            customer_id=estimate.customer_id,
            project_type=estimate.project_type,
            services=estimate.services,
            total_sqft=estimate.total_sqft,
            details=estimate.details,
            sketch_filename=estimate.sketch_filename,
            status='Pending Schedule'  # Project is born here
        )
        db.session.add(project)

    db.session.commit()

    flash("Estimate approved and converted to project.")
    return redirect(url_for('main.customer_dashboard'))


@bp.route('/estimate/<int:estimate_id>/decline')
@login_required
def decline_estimate(estimate_id):
    estimate = EstimateRequest.query.get_or_404(estimate_id)

    if estimate.customer_id != current_user.id:
        return redirect(url_for('main.customer_dashboard'))

    estimate.status = 'Declined'
    estimate.customer_response = 'Declined'
    db.session.commit()

    flash("Estimate declined.")
    return redirect(url_for('main.customer_dashboard'))


# 🔧 Form class for scheduling
class ScheduleForm(FlaskForm):
    # We'll add date fields dynamically
    submit = SubmitField("Send Schedule to Customer")


@bp.route('/admin/project/<int:project_id>/schedule', methods=['GET', 'POST'])
@login_required
def schedule_project(project_id):
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    project = Project.query.get_or_404(project_id)

    # Convert services to list
    service_list = project.services.split(',')

    # Create dynamic fields in the form
    class DynamicScheduleForm(ScheduleForm):
        pass

    for service in service_list:
        field_name = service.strip().replace(" ", "_").lower()
        setattr(
            DynamicScheduleForm,
            field_name,
            DateField(service.strip(), validators=[Optional()])
        )

    form = DynamicScheduleForm()

    if form.validate_on_submit():
        # Save selected dates as a dictionary
        service_dates = {}
        for service in service_list:
            field_name = service.strip().replace(" ", "_").lower()
            selected_date = getattr(form, field_name).data
            if selected_date:
                service_dates[service.strip()] = selected_date.strftime('%Y-%m-%d')

        # Save the schedule to project
        project.schedule_data = service_dates

        # ✅ Set correct status
        project.status = 'Waiting for Schedule Approval'

        db.session.commit()

        flash("Schedule submitted to customer for approval.")
        return redirect(url_for('main.admin_dashboard'))

    return render_template('schedule_project.html', form=form, project=project, services=service_list)

@bp.route('/project/<int:project_id>/approve-schedule')
@login_required
def approve_schedule(project_id):
    project = Project.query.get_or_404(project_id)
    if project.customer_id != current_user.id:
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    project.status = 'Schedule Approved'
    db.session.commit()
    flash("Schedule approved. Project is now in progress.")
    return redirect(url_for('main.track_projects'))


@bp.route('/project/<int:project_id>/request-new-schedule')
@login_required
def request_new_schedule(project_id):
    project = Project.query.get_or_404(project_id)
    if project.customer_id != current_user.id:
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    project.status = 'Pending Schedule'
    db.session.commit()
    flash("Schedule rejected. Admin will assign new dates.")
    return redirect(url_for('main.track_projects'))

@bp.route('/admin/new-project', methods=['GET', 'POST'])
@login_required
def create_new_project():
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    from app.forms import SERVICES  # service types

    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email'].strip()
        project_type = request.form['project_type']
        services = request.form.getlist('services')
        total_sqft = request.form['total_sqft']
        details = request.form['details']
        sketch = request.files.get('sketch')

        # Try to find existing customer
        user = None
        if email:
            user = User.query.filter_by(email=email).first()

        # Handle sketch upload
        sketch_filename = None
        if sketch:
            sketch_filename = secure_filename(sketch.filename)
            upload_path = os.path.join(current_app.root_path, 'static/uploads')
            os.makedirs(upload_path, exist_ok=True)
            sketch.save(os.path.join(upload_path, sketch_filename))

        # Generate project number
        project_number = f"PROJ-{uuid.uuid4().hex[:8].upper()}"

        # Determine project status
        if user:
            status = 'Pending Schedule'
        else:
            status = 'Waiting Assignment'

        # Create project
        project = Project(
            project_number=project_number,
            customer_id=user.id if user else None,
            project_type=project_type,
            services=",".join(services),
            total_sqft=total_sqft,
            details=details,
            sketch_filename=sketch_filename,
            status=status
        )
        db.session.add(project)
        db.session.commit()

        flash('Project created successfully.')
        return redirect(url_for('main.admin_dashboard'))

    services_json = SERVICES
    return render_template('admin_new_project.html', services_json=services_json)



@bp.route('/admin/project/<int:project_id>/upload', methods=['POST'])
@login_required
def upload_project_file(project_id):
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('main.admin_dashboard'))

    form = ProjectUploadForm()
    project = Project.query.get_or_404(project_id)

    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)

        upload_path = os.path.join(current_app.root_path, 'static/project_uploads')
        os.makedirs(upload_path, exist_ok=True)

        file_path = os.path.join(upload_path, filename)
        file.save(file_path)

        # Save record in DB
        upload = ProjectUpload(
            project_id=project.id,
            filename=filename
        )
        db.session.add(upload)
        db.session.commit()

        flash("File uploaded successfully.")
    else:
        flash("Invalid upload.")

    return redirect(url_for('main.view_project_admin', project_id=project.id))


@bp.route('/project/<int:project_id>/message', methods=['POST'])
@login_required
def send_project_message(project_id):
    project = Project.query.get_or_404(project_id)

    # Determine sender role
    if current_user.role not in ['customer', 'admin']:
        flash("Unauthorized")
        return redirect(url_for('main.index'))

    content = request.form.get('message')
    if content:
        message = ProjectMessage(
            project_id=project.id,
            sender=current_user.role,
            content=content
        )
        db.session.add(message)
        db.session.commit()
        flash("Message sent.")
    else:
        flash("Message cannot be empty.")

    # Redirect based on role
    if current_user.role == 'admin':
        return redirect(url_for('main.view_project_admin', project_id=project.id))
    else:
        return redirect(url_for('main.track_projects'))


    message_text = request.form.get('message')
    if message_text:
        msg = ProjectMessage(project_id=project.id, sender='customer', content=message_text)
        db.session.add(msg)
        db.session.commit()

        flash('Message sent.')
    return redirect(url_for('main.track_projects'))

@bp.route('/admin/projects/manage')
@login_required
def manage_projects():
    if current_user.role != 'admin':
        return redirect(url_for('main.customer_dashboard'))

    # Projects sorted by status
    in_progress = Project.query.filter(Project.status.in_(['Pending Schedule', 'Schedule Approved'])).all()
    waiting = Project.query.filter(Project.status == 'Waiting for Schedule Approval').all()
    completed = Project.query.filter(Project.status == 'Completed').all()

    return render_template('manage_projects.html',
                           in_progress=in_progress,
                           waiting=waiting,
                           completed=completed)

@bp.route('/admin/project/<int:project_id>/view', methods=['GET', 'POST'])
@login_required
def view_project_admin(project_id):
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    project = Project.query.get_or_404(project_id)
    customer = project.customer
    messages = ProjectMessage.query.filter_by(project_id=project.id).order_by(ProjectMessage.timestamp.desc()).all()
    uploads = ProjectUpload.query.filter_by(project_id=project.id).order_by(ProjectUpload.timestamp.desc()).all()

    return render_template(
        'view_project_admin.html',
        project=project,
        customer=customer,
        messages=messages,
        uploads=uploads
    )

@bp.route('/admin/project/<int:project_id>/complete', methods=['POST'])
@login_required
def mark_project_complete(project_id):
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('main.admin_dashboard'))

    project = Project.query.get_or_404(project_id)
    project.status = 'Completed'
    db.session.commit()

    flash(f"Project {project.project_number} marked as completed.")
    return redirect(url_for('main.view_project_admin', project_id=project_id))

@bp.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    if current_user.role != 'admin':
        flash("Access denied.")
        return redirect(url_for('main.customer_dashboard'))

    project = Project.query.get_or_404(project_id)

    # Optional: delete related messages and uploads explicitly
    ProjectMessage.query.filter_by(project_id=project.id).delete()
    ProjectUpload.query.filter_by(project_id=project.id).delete()

    db.session.delete(project)
    db.session.commit()

    flash(f"Project {project.project_number} deleted successfully.")
    return redirect(url_for('main.manage_projects'))
