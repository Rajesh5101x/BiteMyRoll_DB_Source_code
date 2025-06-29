from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, DateField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, Optional, NumberRange, EqualTo


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

