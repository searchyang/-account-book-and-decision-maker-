"""项目常量：路径、分类、默认预算。改这里即可，不必翻业务代码。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 本地默认用 SQLite，部署到云上时改用环境变量 DATABASE_URL（PostgreSQL）
DEFAULT_SQLITE_PATH = os.path.join(DATA_DIR, "app.db")

# 开发环境占位密钥。正式上线必须设置环境变量 SECRET_KEY，否则 session 可被伪造
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-before-deploy")

DEFAULT_MONTHLY_BUDGET = 3000.00

# 记账分类做成列表，方便页面循环渲染，也方便以后决策页复用
EXPENSE_CATEGORIES = [
    "餐饮",
    "交通",
    "购物",
    "日用",
    "娱乐",
    "住房",
    "医疗",
    "其他",
]

PASSWORD_MIN_LENGTH = 6


def build_database_url():
    """
    优先读云平台提供的 DATABASE_URL。
    Render 等平台有时给出 postgres://，SQLAlchemy 需要 postgresql://，这里统一转换。
    """
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        os.makedirs(DATA_DIR, exist_ok=True)
        # 三个斜杠表示相对/绝对本地文件路径
        sqlite_path = DEFAULT_SQLITE_PATH.replace("\\", "/")
        return f"sqlite:///{sqlite_path}"
    if raw_url.startswith("postgres://"):
        return "postgresql://" + raw_url[len("postgres://") :]
    return raw_url
