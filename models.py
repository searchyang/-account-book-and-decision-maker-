"""数据表定义。用 user_id 把每个用户的账本隔开，这是多端登录后数据不串号的关键。"""
from datetime import date, datetime

from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    monthly_budget = db.Column(db.Numeric(10, 2), nullable=False, default=3000)
    # 现有总额：用户自己登记「手里有多少钱」。空表示还没登记，记支出时不会乱扣
    cash_balance = db.Column(db.Numeric(10, 2), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    expenses = db.relationship(
        "Expense",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(200), nullable=False, default="")
    spent_on = db.Column(db.Date, nullable=False, default=date.today, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
