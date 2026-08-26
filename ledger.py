"""记账业务：金额校验、增删、今日/本月汇总。查询一律带 user_id，防止看到别人的账。"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from config import DEFAULT_MONTHLY_BUDGET, EXPENSE_CATEGORIES
from database import db
from models import Expense, User


def parse_amount(text):
    """把表单里的金额转成两位小数。格式不对或小于等于 0 时返回 None。"""
    if text is None:
        return None
    cleaned = str(text).strip().replace(",", "").replace("￥", "").replace("¥", "")
    try:
        amount = Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None
    return amount


def parse_spent_on(text):
    """日期为空则用今天。格式必须是 2026-08-26。"""
    if not text:
        return date.today()
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def add_expense(user_id, amount_text, category, note, date_text):
    if category not in EXPENSE_CATEGORIES:
        return False, "分类无效，请重新选择。"

    amount = parse_amount(amount_text)
    if amount is None:
        return False, "金额必须是大于 0 的数字，例如 18.5"

    spent_on = parse_spent_on(date_text)
    if spent_on is None:
        return False, "日期格式不对，请用 2026-08-26 这种格式。"

    try:
        expense = Expense(
            user_id=user_id,
            amount=amount,
            category=category,
            note=(note or "").strip()[:200],
            spent_on=spent_on,
        )
        db.session.add(expense)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return False, f"保存失败，请稍后重试。原因：{error}"
    return True, f"已记账：{spent_on}  {category}  {amount} 元"


def delete_expense(user_id, expense_id):
    """删除时同时校验归属，避免用别人的编号删账。"""
    expense = db.session.get(Expense, expense_id)
    if expense is None or expense.user_id != user_id:
        return False, "找不到这笔账，或无权删除。"
    try:
        db.session.delete(expense)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return False, f"删除失败：{error}"
    return True, "已删除该笔记账。"


def list_month_expenses(user_id, year, month):
    start_day = date(year, month, 1)
    if month == 12:
        end_day = date(year + 1, 1, 1)
    else:
        end_day = date(year, month + 1, 1)
    return (
        Expense.query.filter(
            Expense.user_id == user_id,
            Expense.spent_on >= start_day,
            Expense.spent_on < end_day,
        )
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
        .all()
    )


def sum_amount(records):
    total = Decimal("0.00")
    for item in records:
        total += item.amount
    return total.quantize(Decimal("0.01"))


def category_summary(records):
    summary = {}
    for item in records:
        current = summary.get(item.category, Decimal("0.00"))
        summary[item.category] = (current + item.amount).quantize(Decimal("0.01"))
    sorted_items = sorted(summary.items(), key=lambda pair: pair[1], reverse=True)
    return sorted_items


def build_today_summary(user_id):
    today = date.today()
    records = (
        Expense.query.filter(
            Expense.user_id == user_id,
            Expense.spent_on == today,
        )
        .order_by(Expense.id.desc())
        .all()
    )
    return {
        "date": today,
        "total": sum_amount(records),
        "records": records,
        "count": len(records),
    }


def build_month_summary(user_id, year=None, month=None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    user = db.session.get(User, user_id)
    budget = user.monthly_budget if user else Decimal(str(DEFAULT_MONTHLY_BUDGET))
    records = list_month_expenses(user_id, year, month)
    total = sum_amount(records)
    remain = (budget - total).quantize(Decimal("0.01"))
    percent = 0.0
    if budget > 0:
        percent = float((total / budget * 100).quantize(Decimal("0.1")))
    bar_width = min(max(percent, 0.0), 100.0)
    return {
        "year": year,
        "month": month,
        "total": total,
        "budget": budget,
        "remain": remain,
        "percent": min(percent, 999.9),
        "bar_width": bar_width,
        "over_budget": remain < 0,
        "tight": remain >= 0 and budget > 0 and remain < (budget * Decimal("0.2")),
        "records": records,
        "categories": category_summary(records),
        "count": len(records),
    }


def set_monthly_budget(user_id, amount_text):
    amount = parse_amount(amount_text)
    if amount is None:
        return False, "预算必须是大于 0 的数字，例如 3000"
    user = db.session.get(User, user_id)
    if user is None:
        return False, "找不到当前用户，请重新登录。"
    try:
        user.monthly_budget = amount
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return False, f"保存预算失败：{error}"
    return True, f"本月预算已设为 {amount} 元"
