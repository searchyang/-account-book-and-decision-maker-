"""单独放 SQLAlchemy 对象，避免 models 和 app 互相循环导入。"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
