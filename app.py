"""Flask 入口：页面路由。业务计算放在 ledger.py，这里只负责取表单、调函数、渲染页面。"""
from datetime import date, timedelta

from flask import Flask, flash, redirect, render_template, request, url_for

from auth_helpers import (
    check_csrf,
    create_user,
    current_user_id,
    find_user_by_email,
    get_csrf_token,
    get_current_user,
    login_required,
    login_user,
    logout_user,
    validate_register_input,
    verify_password,
)
from config import EXPENSE_CATEGORIES, SECRET_KEY, build_database_url
from database import db, ensure_extra_columns
from ledger import (
    add_expense,
    build_month_summary,
    build_today_summary,
    delete_expense,
    get_cash_balance,
    set_cash_balance,
    set_monthly_budget,
)
import models  # noqa: F401  导入模型后 create_all 才能建表


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = build_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # 记住登录 30 天，换手机打开同一网址时少输一次密码
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_extra_columns()

    @app.context_processor
    def inject_common():
        return {
            "csrf_token": get_csrf_token(),
            "current_user": get_current_user(),
            "today_iso": date.today().isoformat(),
            "categories": EXPENSE_CATEGORIES,
        }

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.errorhandler(400)
    def handle_bad_request(error):
        message = getattr(error, "description", None) or "请求无效，请刷新后重试。"
        return render_template("error.html", message=message), 400

    @app.route("/")
    def index():
        if current_user_id():
            return redirect(url_for("home"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user_id():
            return redirect(url_for("home"))
        if request.method == "POST":
            check_csrf()
            email, error = validate_register_input(
                request.form.get("email"),
                request.form.get("password"),
                request.form.get("confirm_password"),
            )
            if error:
                flash(error, "error")
                return render_template("register.html")
            try:
                user = create_user(email, request.form.get("password"))
            except Exception as err:
                db.session.rollback()
                flash(f"注册失败：{err}", "error")
                return render_template("register.html")
            login_user(user)
            flash("注册成功，已经登录。建议先登记现有多少钱。", "ok")
            return redirect(url_for("home"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user_id():
            return redirect(url_for("home"))
        if request.method == "POST":
            check_csrf()
            user = find_user_by_email(request.form.get("email"))
            password = request.form.get("password") or ""
            if user is None or not verify_password(user.password_hash, password):
                flash("邮箱或密码不对。", "error")
                return render_template("login.html")
            login_user(user)
            return redirect(url_for("home"))
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        check_csrf()
        logout_user()
        flash("已退出登录。", "ok")
        return redirect(url_for("login"))

    @app.get("/home")
    @login_required
    def home():
        user_id = current_user_id()
        return render_template(
            "home.html",
            today_summary=build_today_summary(user_id),
            month_summary=build_month_summary(user_id),
            cash_balance=get_cash_balance(user_id),
            nav="home",
        )

    @app.post("/expenses")
    @login_required
    def create_expense():
        check_csrf()
        ok, message = add_expense(
            user_id=current_user_id(),
            amount_text=request.form.get("amount"),
            category=request.form.get("category") or "其他",
            note=request.form.get("note"),
            date_text=request.form.get("spent_on"),
        )
        flash(message, "ok" if ok else "error")
        next_page = request.form.get("next") or "home"
        if next_page == "expenses":
            return redirect(url_for("expenses"))
        return redirect(url_for("home"))

    @app.get("/expenses")
    @login_required
    def expenses():
        today = date.today()
        try:
            year = int(request.args.get("year", today.year))
            month = int(request.args.get("month", today.month))
        except ValueError:
            year, month = today.year, today.month
        if month < 1 or month > 12 or year < 2000 or year > 2100:
            year, month = today.year, today.month
        summary = build_month_summary(current_user_id(), year, month)
        grouped = group_records_by_date(summary["records"])
        return render_template(
            "expenses.html",
            month_summary=summary,
            grouped=grouped,
            cash_balance=get_cash_balance(current_user_id()),
            nav="expenses",
        )

    @app.post("/expenses/<int:expense_id>/delete")
    @login_required
    def remove_expense(expense_id):
        check_csrf()
        ok, message = delete_expense(current_user_id(), expense_id)
        flash(message, "ok" if ok else "error")
        return redirect(url_for("expenses"))

    @app.post("/cash-balance")
    @login_required
    def update_cash_balance():
        check_csrf()
        ok, message = set_cash_balance(
            current_user_id(),
            request.form.get("cash_balance"),
        )
        flash(message, "ok" if ok else "error")
        next_page = request.form.get("next") or "home"
        if next_page == "settings":
            return redirect(url_for("settings"))
        return redirect(url_for("home"))

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        if request.method == "POST":
            check_csrf()
            ok, message = set_monthly_budget(
                current_user_id(),
                request.form.get("monthly_budget"),
            )
            flash(message, "ok" if ok else "error")
            return redirect(url_for("settings"))
        return render_template(
            "settings.html",
            nav="settings",
            month_summary=build_month_summary(current_user_id()),
            cash_balance=get_cash_balance(current_user_id()),
        )

    return app


def group_records_by_date(records):
    """按日期分组，明细页才能做成日历那种一块一块的列表。"""
    groups = []
    current_day = None
    bucket = []
    for item in records:
        if current_day != item.spent_on:
            if bucket:
                groups.append({"day": current_day, "records": bucket})
            current_day = item.spent_on
            bucket = [item]
        else:
            bucket.append(item)
    if bucket:
        groups.append({"day": current_day, "records": bucket})
    return groups


app = create_app()


if __name__ == "__main__":
    # 0.0.0.0 允许同一 WiFi 下的手机访问这台电脑，方便先本地试双端
    app.run(host="0.0.0.0", port=5000, debug=True)
