"""认证层 —— 手机号+密码 登录 / 游客凭证 / 登录合并

身份模型(豆包式):
    - 每台设备/每个访客都有一个身份: 未登录时是"匿名用户"(is_guest=1),
      登录后是正式用户(is_guest=0)。都存 users 表, user_id 都从 10000 自增。
    - 游客凭证 = 匿名用户的 token, 前端存本地, 每次请求带上。
    - 单token模型: 同一身份只保留最新一个token, 重新登录顶掉旧的(旧设备被强制下线)。
    - 注册时可带 X-Guest-Token: 给这个匿名用户"转正"(补手机号密码, id不变, 数据无缝)。
    - 登录就是登录: 游客数据留在游客身份上, 账号用自己的数据, 互不合并。
    - 退出登录只作废正式token; 前端再领一个新游客凭证 → 回到清零的游客态。
"""
import re
import uuid
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from chatbot.memory import query

TOKEN_DAYS = 7
USER_ID_START = 10000
PHONE_RE = re.compile(r"^1\d{10}$")

# ---------- 建表(含旧结构迁移: phone 允许为空 + is_guest 标记) ----------
_cols = query("PRAGMA table_info(users)", fetch=True) or []
if _cols and "is_guest" not in [c["name"] for c in _cols]:
    query("""
        CREATE TABLE users_new (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phone         TEXT UNIQUE,
            password_hash TEXT,
            is_guest      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        )""")
    query("""INSERT INTO users_new (id, phone, password_hash, is_guest, created_at)
             SELECT id, phone, password_hash, 0, created_at FROM users""")
    query("DROP TABLE users")
    query("ALTER TABLE users_new RENAME TO users")
query("""
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,   -- 5位数起步
    phone         TEXT UNIQUE,                          -- 游客为空
    password_hash TEXT,                                 -- 游客为空
    is_guest      INTEGER NOT NULL DEFAULT 0,           -- 1=匿名用户
    created_at    TEXT NOT NULL
)
""")
query("""
CREATE TABLE IF NOT EXISTS tokens (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
)
""")
# 单token模型: 只保留每个身份最新的一个token(历史重复数据清理), 唯一索引兜底
# 注: 只是清理历史遗留数据, 就算数据库暂时被占用也跳过, 不阻塞启动
#     (登录时的 DELETE-再-INSERT 已经在运行时保证单token)
try:
    query("DELETE FROM tokens WHERE rowid NOT IN "
          "(SELECT MAX(rowid) FROM tokens GROUP BY user_id)")
    query("CREATE UNIQUE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id)")
except Exception as e:
    print(f"[warn] tokens 历史清理跳过(数据库被占用): {e} ; 下次启动会重试")
# user_id 预置从 10000 开始
query("INSERT INTO sqlite_sequence (name, seq) SELECT 'users', ? "
      "WHERE NOT EXISTS (SELECT 1 FROM sqlite_sequence WHERE name = 'users')",
      (USER_ID_START - 1,))
query("UPDATE sqlite_sequence SET seq = ? WHERE name = 'users' AND seq < ?",
      (USER_ID_START - 1, USER_ID_START - 1))


class AuthError(Exception):
    """认证业务错误, 消息可直接返回给前端"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _issue_token(user_id: int) -> dict:
    """发token; 单token模型: 新token签发前先作废该身份的全部旧token"""
    query("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    token = uuid.uuid4().hex
    expires_at = (datetime.now() + timedelta(days=TOKEN_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    query("INSERT INTO tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
          (token, user_id, _now(), expires_at))
    return {"token": token, "expires_at": expires_at}


# ---------- 游客凭证 ----------
def create_guest() -> dict:
    """发一个匿名用户身份: 建行 + 发token"""
    # INSERT 的返回值就是自增ID(lastrowid, 同连接内取才有效; query 每次是新连接)
    user_id = query("INSERT INTO users (is_guest, created_at) VALUES (1, ?)", (_now(),))
    result = _issue_token(user_id)
    return {"message": "游客身份已创建", "user_id": user_id, **result}


# ---------- 注册(可带游客转正) ----------
def register(phone: str, password: str, upgrade_user_id: int | None = None) -> dict:
    phone = (phone or "").strip()
    if not PHONE_RE.fullmatch(phone):
        raise AuthError("手机号格式不正确(1开头的11位数字)")
    if len(password or "") < 6:
        raise AuthError("密码至少 6 位")

    if upgrade_user_id:
        # 游客转正: 原行补上手机号密码, id 和数据全部保留
        rows = query("SELECT * FROM users WHERE id = ?", (upgrade_user_id,), fetch=True)
        if not rows or not rows[0]["is_guest"]:
            raise AuthError("游客凭证无效，无法转正")
        dup = query("SELECT id FROM users WHERE phone = ? AND id != ?",
                    (phone, upgrade_user_id), fetch=True)
        if dup:
            raise AuthError("该手机号已注册")
        query("UPDATE users SET phone = ?, password_hash = ?, is_guest = 0 WHERE id = ?",
              (phone, generate_password_hash(password), upgrade_user_id))
        return {"message": "注册成功，历史数据已保留", "user_id": upgrade_user_id, "phone": phone}

    # 普通注册
    if query("SELECT id FROM users WHERE phone = ?", (phone,), fetch=True):
        raise AuthError("该手机号已注册")
    user_id = query(
        "INSERT INTO users (phone, password_hash, is_guest, created_at) VALUES (?, ?, 0, ?)",
        (phone, generate_password_hash(password), _now()))
    return {"message": "注册成功，请登录", "user_id": user_id, "phone": phone}


# ---------- 登录 ----------
def login(phone: str, password: str) -> dict:
    """校验手机号密码并签发token(单token: 顶掉该账号旧token); 与游客数据无关"""
    rows = query("SELECT * FROM users WHERE phone = ?", ((phone or "").strip(),), fetch=True)
    if not rows:
        raise AuthError("该手机号未注册，请先注册")
    if not check_password_hash(rows[0]["password_hash"], password or ""):
        raise AuthError("手机号或密码错误")
    user = rows[0]
    result = _issue_token(user["id"])
    return {"message": "登录成功", "user_id": user["id"],
            "phone": user["phone"], **result}


def user_from_token(token: str | None) -> dict | None:
    token = (token or "").strip()
    if not token:
        return None
    rows = query(
        "SELECT u.id AS user_id, u.phone, u.is_guest FROM tokens t "
        "JOIN users u ON u.id = t.user_id "
        "WHERE t.token = ? AND t.expires_at > ?",
        (token, _now()), fetch=True,
    )
    return rows[0] if rows else None


def logout(token: str | None) -> bool:
    if not (token or "").strip():
        return False
    query("DELETE FROM tokens WHERE token = ?", (token.strip(),))
    return True
