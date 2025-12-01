from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, DateField, PasswordField, SubmitField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, Optional, NumberRange, EqualTo, Regexp


class signupForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(4,20)
        ]
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    ) 



    gender = SelectField(
        "Gender",
        choices = [(None,"--Choose Gender--"),("Male","Male"), ("Female","Female"), ("Others","Others")],
        validators=[
            Optional()
        ]
    )

    dob = DateField(
        "Date Of Birth",
        validators=[
            DataRequired()
        ]
    )

    phone = StringField(
        "Phone Number",
        validators=[
            DataRequired(),
            Regexp(r'^[0-9]{10}$', message="Enter a valid 10-digit phone number")
        ]
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(), 
            Length(min=6)
        ]
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(), 
            EqualTo('password')
        ]
    )
    remember = BooleanField("Remember Me",default=False)


    submit = SubmitField("Sign Up")
    

class loginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    ) 

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(), 
            Length(min=6)
        ]
    )

    remember = BooleanField("Remember Me",default=False)

    submit = SubmitField("Login")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired()]
    )
    password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Change Password")



class ContactForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    category = SelectField('Category', choices=[
        ('feedback', 'Feedback'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion')
    ], validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Submit')




class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Role', choices=[('2', 'Staff'), ('3', 'Delivery Boy')], coerce=int)
    submit = SubmitField('Create User')
