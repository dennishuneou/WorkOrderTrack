from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, InputRequired
from app.auth.models import User
#role  [(0,'Assemble Technican'),(1,'Quality Inspector'),(2,'Quality Manager'),(3,'Supervisor')]]
def email_exists(form, field):
    email = User.query.filter_by(user_email=field.data).first()
    if email:
        raise ValidationError('Email already exists')
def username_exists(form, field):
    user_name = User.query.filter_by(user_name=field.data).first()
    if user_name:
        raise ValidationError('User_name already exists')

def get_usersname():
    return User.query.all().filter(User.status > 0)
def get_operateusersname():
    return User.query.filter(User.role < 3).filter(User.status > 0)
def get_username(userid):
    users = User.query.filter_by(id=userid)
    if users.count() :
        return users[0].user_name
    else :
        return ''
def get_useridbyname(username) :
    print(username)
    users = User.query.filter_by(user_name=username)
    if users.count() :
        print("username")
        return users[0].id 
    else :
        print("not find")
        return -1

def get_userrole(userid):
     roles = User.query.filter_by(id=userid)
     if roles.count() :
        return roles[0].role
     else :
        return 0   
    
class RegistrationForm(FlaskForm):
    name = StringField("Whats your name", validators=[DataRequired(), Length(3, 15, message='between 3 to 15 characters'), InputRequired(),username_exists])
    email = StringField("Enter your email", validators=[DataRequired(), Email(), email_exists])
    password = PasswordField("Password", validators=[DataRequired(), Length(5), EqualTo('confirm_password', message='passwords should match' )])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])
    role = SelectField('Role',coerce=int, choices=[(0,'Assemble Technican'),(1,'Quality Inspector'),(2,'Quality Manager'),(3,'Supervisor')])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    stay_loggedin = BooleanField('stay logged in')
    submit = SubmitField('LogIn')



