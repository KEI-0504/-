import os
from datetime import date
#from decimal import Decimal
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from models import db, Category, Transaction, seed_categories, User
from forms import TransactionForm, RegisterForm, LoginForm
from collections import defaultdict
import calendar
from collections import defaultdict

app = Flask(__name__)

# ★ 環境変数から値を取る（クラウドで安全）
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ★ DBは環境変数 DATABASE_URL があればそれを採用（RenderのPostgres）
import os
# ...
db_url = os.getenv("DATABASE_URL")
if db_url:
    # 旧 'postgres://' を psycopg3 用に
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    # 必要なら SSL 付与（RenderのURLに既に付いていれば不要）
    if "sslmode=" not in db_url:
        sep = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{sep}sslmode=require"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kakeibo.db"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
csrf = CSRFProtect(app)

# --- Flask-Login 設定 ---
login_manager = LoginManager(app)
login_manager.login_view = "login"          # 未ログイン時のリダイレクト先
login_manager.login_message = "ログインしてください。"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def _set_category_choices(form):
    """カテゴリ選択肢をフォームへ設定"""
    cats = Category.query.order_by(Category.kind.desc(), Category.name).all()
    form.category_id.choices = [
        (c.id, f"{'支出' if c.kind=='expense' else '収入'} | {c.name}") for c in cats
    ]

# ----- 認証ルート -----
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("このユーザー名は既に使われています。")
            return render_template("register.html", form=form)

        user = User(username=form.username.data, email=form.email.data or None)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("登録が完了しました。ログインしてください。")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user or not user.check_password(form.password.data):
            flash("ユーザー名またはパスワードが正しくありません。")
            return render_template("login.html", form=form)
        login_user(user)
        flash("ログインしました。")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard"))
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    return redirect(url_for("dashboard"))

@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    form = TransactionForm()
    _set_category_choices(form)  # ← 共通関数で選択肢設定

    if form.validate_on_submit():
        t = Transaction(
            date=form.date.data,
            description=form.description.data.strip(),
            amount=form.amount.data,
            kind=form.kind.data,
            category_id=form.category_id.data,
            user_id=current_user.id
        )
        db.session.add(t)
        db.session.commit()
        flash("取引を登録しました。")
        return redirect(url_for("transactions"))

    items = (Transaction.query
             .filter_by(user_id=current_user.id)    # ★自分のデータのみ
             .order_by(Transaction.date.desc(), Transaction.id.desc())
             .all())
    return render_template("transactions.html", form=form, items=items)

@app.route("/transactions/delete/<int:tx_id>", methods=["POST"])
@login_required
def delete_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    db.session.delete(tx)
    db.session.commit()
    flash("取引を削除しました。")
    return redirect(url_for("transactions"))

@app.route("/transactions/edit/<int:tx_id>", methods=["GET", "POST"])
@login_required
def edit_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    form = TransactionForm(obj=tx)
    _set_category_choices(form)
    if request.method == "GET":
        form.category_id.data = tx.category_id

    if form.validate_on_submit():
        tx.date        = form.date.data
        tx.description = form.description.data.strip()
        tx.amount      = form.amount.data
        tx.kind        = form.kind.data
        tx.category_id = form.category_id.data
        db.session.commit()
        flash("取引を更新しました。")
        return redirect(url_for("transactions"))
    return render_template("edit_transaction.html", form=form, tx=tx)

@app.route("/dashboard")
@login_required
def dashboard():
    # ---- 月の指定（?y=2025&m=9 など） ----
    y = request.args.get("y", type=int)
    m = request.args.get("m", type=int)

    today = date.today()
    year = y or today.year
    month = m or today.month

    # 週の先頭を「日曜」に（日本の家計簿っぽく）
    calendar.setfirstweekday(calendar.SUNDAY)

    month_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    next_month_start = date(year + (1 if month == 12 else 0),
                            1 if month == 12 else month + 1, 1)
    # 前月/翌月（ナビ用）
    prev_year  = year - 1 if month == 1  else year
    prev_month = 12        if month == 1  else month - 1
    next_year  = year + 1  if month == 12 else year
    next_month = 1         if month == 12 else month + 1

    # ---- データ取得（当該月・ログインユーザー分のみ）----
    this_month = (Transaction.query
                  .filter(Transaction.user_id == current_user.id,
                          Transaction.date >= month_start,
                          Transaction.date < next_month_start)
                  .all())

    # 収支集計
    income  = sum(t.amount for t in this_month if t.kind == "income")
    expense = sum(t.amount for t in this_month if t.kind == "expense")
    balance = income - expense

    # カテゴリ別支出（円グラフ＆表）
    by_cat = defaultdict(int)
    for t in this_month:
        if t.kind == "expense":
            by_cat[t.category.name if t.category else "未分類"] += t.amount
    cat_rows   = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
    cat_labels = [name for name, _total in cat_rows]
    cat_values = [total for _name, total in cat_rows]

    # 日別の合計（支出/収入/収支）
    daily_income  = [0] * last_day
    daily_expense = [0] * last_day
    daily_balance = [0] * last_day
    for t in this_month:
        d = t.date.day
        if t.kind == "income":
            daily_income[d - 1] += t.amount
        else:
            daily_expense[d - 1] += t.amount
        daily_balance[d - 1] = daily_income[d - 1] - daily_expense[d - 1]

    # カレンダーのマトリクス（0は前後月のパディング）
    weeks = calendar.monthcalendar(year, month)  # [[Sun..Sat], …]

    # 棒グラフ（日別支出）用の軸
    day_labels = [f"{d}日" for d in range(1, last_day + 1)]
    day_values = daily_expense  # 支出のみ

    return render_template(
        "dashboard.html",
        # ヘッダ/ナビ
        year=year, month=month, month_str=f"{year}年{month:02d}月",
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,

        # 既存のカード/表
        income=income, expense=expense, balance=balance, cat_rows=cat_rows,

        # グラフ用
        cat_labels=cat_labels, cat_values=cat_values,
        day_labels=day_labels, day_values=day_values,

        # カレンダー用
        weeks=weeks,
        daily_income=daily_income,
        daily_expense=daily_expense,
        daily_balance=daily_balance
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_categories()
    app.run(debug=True)