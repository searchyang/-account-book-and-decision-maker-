"""单独放 SQLAlchemy 对象，避免 models 和 app 互相循环导入。"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()


def ensure_extra_columns():
    """
    create_all 不会给已经存在的表加新列。
    老用户升级时补上 cash_balance，否则读写会报错。
    """
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return
    column_names = [item["name"] for item in inspector.get_columns("users")]
    if "cash_balance" in column_names:
        return
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN cash_balance NUMERIC(10, 2)"))
