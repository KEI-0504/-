from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    transactions = relationship("Transaction", back_populates="user")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # kind: "expense" or "income"
    kind = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    __table_args__ = (
        CheckConstraint("kind IN ('expense','income')", name="ck_category_kind"),
    )

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # "expense" or "income"
    category_id = db.Column(db.Integer, ForeignKey("category.id"))
    user_id     = db.Column(db.Integer, ForeignKey("user.id"), nullable=False)
    
    
    category = relationship("Category")
    user     = relationship("User", back_populates="transactions")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("kind IN ('expense','income')", name="ck_tx_kind"),
    )

def seed_categories():
    """初回起動時にデフォルトカテゴリを投入"""
    if Category.query.count() > 0:
        return
    expense_names = ["食費", "住居", "光熱費", "通信", "交通", "教養娯楽", "日用品", "医療", "交際費", "特別費", "税金", "その他"]
    income_names = ["給与", "副収入", "賞与"]
    for n in expense_names:
        db.session.add(Category(kind="expense", name=n))
    for n in income_names:
        db.session.add(Category(kind="income", name=n))
    db.session.commit()
