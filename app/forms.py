from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, FileField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Email, EqualTo, Length
from flask_wtf.file import FileAllowed, FileRequired, FileField
from wtforms import MultipleFileField  # ← make sure this is imported

# -------------------
# Registration & Login
# -------------------
class RegisterForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# -------------------
# Custom MultiCheckbox
# -------------------
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

# -------------------
# Project & Estimate Choices
# -------------------
PROJECT_TYPES = [
    ('Kitchen Remodel', 'Kitchen Remodel'),
    ('Bath Remodel', 'Bath Remodel'),
    ('Flooring', 'Flooring'),
    ('Painting', 'Painting')
]

SERVICES = {
    'Kitchen Remodel': ['Demolition', 'Standard Cabinets', 'Custom Cabinets', 'Flooring', 'Painting', 'Backsplash', 'Countertop', 'Lighting', 'Doors/Windows'],
    'Bath Remodel': ['Demolition', 'Bathtub Replacement', 'Acrylic Shower Replacement', 'Tile Shower', 'Flooring', 'Painting', 'Lighting', 'Cabinets', 'Doors/Windows'],
    'Flooring': ['Old Floor Removal', 'Tile', 'Carpet', 'Hardwood', 'Glue Down', 'Laminate', 'Vinyl', 'Other', 'Re-leveling', 'New Baseboard Install', 'Doors/Windows'],
    'Painting': ['Interior Painting', 'Exterior Painting', 'Patching', 'Priming', 'Trimming', 'Doors/Windows']
}

# -------------------
# Estimate Request Form (Updated with multiple file support)
# -------------------

class EstimateRequestForm(FlaskForm):
    project_type = SelectField('Project Type', choices=PROJECT_TYPES, validators=[DataRequired()])
    services = MultiCheckboxField('Select Services', choices=[])
    total_sqft = IntegerField('Total Square Feet')
    images = MultipleFileField('Upload Sketch / Pictures (up to 5)')  # ✅ updated field
    details = TextAreaField('What do you need done in details (specify)')
    submit = SubmitField('Submit Estimate Request')

# -------------------
# Admin: Upload Estimate PDF
# -------------------
class AdminEstimateUploadForm(FlaskForm):
    estimate_pdf = FileField('Upload Estimate PDF', validators=[DataRequired()])
    submit = SubmitField('Send Estimate to Customer')

# -------------------
# Project: File Upload (Admin or Customer)
# -------------------
class ProjectUploadForm(FlaskForm):
    file = FileField('Select File', validators=[DataRequired()])
    submit = SubmitField('Upload')
