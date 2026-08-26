"""登录校验与 CSRF。CSRF 令牌放在 session 里，是因为表单提交必须证明来自本站页面。"""
import re
import secrets
from functools import wraps

from flask import abort, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import PASSWORD_MIN_LENGTH
from database import db
from models import User

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(plain_text):
    return generate_password_hash(plain_text)


def verify_password(password_hash, plain_text):
    return check_password_hash(password_hash, plain_text)


def normalize_email(email):
    return (email or "").strip().lower()


def validate_register_input(email, password, confirm_password):
    email = normalize_email(email)
    if not EMAIL_PATTERN.match(email):
        return None, "请输入正确的邮箱，例如 name@example.com"
    if len(password or "") < PASSWORD_MIN_LENGTH:
        return None, f"密码至少 {PASSWORD_MIN_LENGTH} 位"
    if password != confirm_password:
        return None, "两次输入的密码不一致"
    existing = User.query.filter_by(email=email).first()
    if existing is not None:
        return None, "这个邮箱已经注册过了，请直接登录。"
    return email, None


def create_user(email, password):
    user = User(email=email, password_hash=hash_password(password))
    db.session.add(user)
    db.session.commit()
    return user


def find_user_by_email(email):
    return User.query.filter_by(email=normalize_email(email)).first()


def login_user(user):
    session.clear()
    session["user_id"] = user.id
    refresh_csrf_token()
    session.permanent = True


def logout_user():
    session.clear()
    refresh_csrf_token()


def current_user_id():
    return session.get("user_id")


def get_current_user():
    user_id = current_user_id()
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def refresh_csrf_token():
    session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = refresh_csrf_token()
    return token


def check_csrf():
    form_token = request.form.get("csrf_token", "")
    session_token = session.get("csrf_token", "")
    if not form_token or not session_token or form_token != session_token:
        abort(400, description="表单已过期，请刷新页面后重试。")
