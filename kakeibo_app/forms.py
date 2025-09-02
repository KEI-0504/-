from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, DateField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Length, Email, EqualTo, Optional

class TransactionForm(FlaskForm):
    date = DateField("日付", default=date.today, validators=[DataRequired()])
    description = StringField("内容", validators=[DataRequired(), Length(max=200)])
    amount = IntegerField("金額",
                          validators=[DataRequired(), NumberRange(min=0)])
    kind = SelectField("種類", choices=[("expense", "支出"), ("income", "収入")],
                       validators=[DataRequired()])
    category_id = SelectField("カテゴリ", coerce=int, validators=[DataRequired()])
    submit = SubmitField("登録")

class RegisterForm(FlaskForm):
    username = StringField("ユーザー名", validators=[DataRequired(), Length(min=3, max=50)])
    email    = StringField("メール（任意）", validators=[Optional(), Email(), Length(max=120)])
    password = PasswordField("パスワード", validators=[DataRequired(), Length(min=6)])
    confirm  = PasswordField("確認用パスワード", validators=[DataRequired(), EqualTo('password')])
    submit   = SubmitField("登録")

class LoginForm(FlaskForm):
    username = StringField("ユーザー名", validators=[DataRequired()])
    password = PasswordField("パスワード", validators=[DataRequired()])
    submit   = SubmitField("ログイン")