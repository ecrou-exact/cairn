from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

from app.features.account.account_core import MIN_PASSWORD_LENGTH

_CODE = [DataRequired(), Regexp(r"^\s*\d{6}\s*$", message="Enter the 6-digit code.")]


class SetupForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH)])
    confirm = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords differ.")]
    )


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=1024)])


class TotpForm(FlaskForm):
    code = StringField("Code", validators=_CODE)


class PasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    new = PasswordField("New password", validators=[DataRequired(), Length(min=MIN_PASSWORD_LENGTH)])
    confirm = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("new", message="Passwords differ.")]
    )
