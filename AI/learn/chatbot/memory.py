"""记忆层 —— 话题(会话)历史持久化到 SQLite, 全部使用整数自增 ID

ID 规则:
    topics.id    从 1 开始自增
    messages.id  从 1 开始自增
    users.id     从 10000 开始自增(5位数, 见 auth.py)
数据库文件: learn/data/ai_chat.db
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

DB_PATH = Path(__file__).parent.parent / "data" / "ai_chat.db"  # 换新文件: 旧 chat.db 被未知进程锁死
DB_PATH.parent.mkdir(exist_ok=True)



def query(sql: str, params: tuple = (), fetch: bool = False):
    """执行一条 SQL: 增删改返回 None, 查询返回字典行列表"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")    # 每个连接都要单独开启外键
    conn.execute("PRAGMA busy_timeout = 5000")  # 遇到锁最多等5秒
    try:
        cur = conn.execute(sql, params)
        if fetch:
            rows = [dict(r) for r in cur.fetchall()]
            conn.commit()
            return rows
        conn.commit()
        return cur.lastrowid   # INSERT 时返回自增ID(同连接内才有效, 所以在这里取)
    finally:
        conn.close()


def init_db() -> None:
    """建表(已存在则跳过); 收成函数方便测试换库后重建"""
    query("""
    CREATE TABLE IF NOT EXISTS topics (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- 从 1 开始
        title      TEXT NOT NULL,
        created_at TEXT NOT NULL,
        user_id    INTEGER NOT NULL                    -- 归属身份ID(游客/正式用户)
    )
    """)
    query("""
    CREATE TABLE IF NOT EXISTS messages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- 从 1 开始
        topic_id   INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
        role       TEXT NOT NULL,                      -- 'human' 或 'ai'
        content    TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    query("""
    CREATE TABLE IF NOT EXISTS context_vectors (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id   INTEGER NOT NULL,
        role       TEXT NOT NULL,
        content    TEXT NOT NULL,
        vector     TEXT NOT NULL,                      -- JSON 数组形式存向量
        created_at TEXT NOT NULL
    )
    """)


init_db()  # 导入时照常建表


class SQLiteChatMessageHistory(InMemoryChatMessageHistory):
    """带数据库持久化的聊天历史: 每条消息实时 INSERT, 读取时从表恢复"""

    topic_id: int  # pydantic 字段必须显式声明

    def __init__(self, topic_id: int, **kwargs):
        super().__init__(topic_id=topic_id, **kwargs)
        rows = query(
            "SELECT role, content FROM messages WHERE topic_id = ? ORDER BY id",
            (topic_id,), fetch=True,
        )
        for r in rows:  # 把数据库里的历史恢复成消息对象
            if r["role"] == "human":
                self.messages.append(HumanMessage(content=r["content"]))
            elif r["role"] == "ai":
                self.messages.append(AIMessage(content=r["content"]))

    @staticmethod
    def _norm_role(message) -> str:
        """规范化 role: 流式输出的 AIMessageChunk.type 是 'AIMessageChunk' 而不是 'ai',
        直接入库会导致前端无法区分用户/AI; 统一归一为 'human'/'ai'"""
        if isinstance(message, AIMessage):   # 覆盖 AIMessage / AIMessageChunk 及其子类
            return "ai"
        if isinstance(message, HumanMessage):
            return "human"
        return getattr(message, "type", "unknown")

    def add_message(self, message) -> None:
        super().add_message(message)
        query(
            "INSERT INTO messages (topic_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (self.topic_id, self._norm_role(message), message.content,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

    def clear(self) -> None:
        super().clear()
        query("DELETE FROM messages WHERE topic_id = ?", (self.topic_id,))


# ---------- 对外接口 ----------
_histories: dict[int, InMemoryChatMessageHistory] = {}  # topic_id -> 历史对象缓存


def create_topic(title: str | None = None, user_id: int | None = None) -> dict:
    """新建话题, id 由数据库从 1 开始自增; user_id 必传(归属身份ID)"""
    if user_id is None:
        raise ValueError("create_topic 必须传 user_id(游客或正式用户的身份ID)")
    meta = {
        "title": title or "新话题",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
    }
    meta["id"] = query("INSERT INTO topics (title, created_at, user_id) VALUES (?, ?, ?)",
                       (meta["title"], meta["created_at"], meta["user_id"]))
    return meta


def get_topic(topic_id: int) -> dict | None:
    rows = query("SELECT * FROM topics WHERE id = ?", (topic_id,), fetch=True)
    return rows[0] if rows else None


def set_topic_title(topic_id: int, title: str) -> None:
    query("UPDATE topics SET title = ? WHERE id = ?", (title, topic_id))


def list_topics(user_id: int | None = None) -> list[dict]:
    """话题列表 + 消息条数; 传 user_id 只看该用户的"""
    sql = """
        SELECT t.id, t.title, t.created_at, t.user_id,
               (SELECT COUNT(*) FROM messages m WHERE m.topic_id = t.id) AS message_count
        FROM topics t
    """
    if user_id is not None:
        return query(sql + " WHERE t.user_id = ? ORDER BY t.created_at DESC",
                     (user_id,), fetch=True) or []
    return query(sql + " ORDER BY t.created_at DESC", fetch=True) or []


def get_messages(topic_id: int) -> list[dict]:
    """某话题的全部聊天记录(按时间正序), 供前端点开话题时回显历史"""
    return query(
        "SELECT id, role, content, created_at FROM messages WHERE topic_id = ? ORDER BY id",
        (topic_id,), fetch=True,
    ) or []


def delete_topic(topic_id: int) -> bool:
    """删除话题; messages 随外键级联删除, 向量行手动清理"""
    if not get_topic(topic_id):
        return False
    query("DELETE FROM context_vectors WHERE topic_id = ?", (topic_id,))
    query("DELETE FROM topics WHERE id = ?", (topic_id,))
    return True


def get_session_history(session_id: int) -> InMemoryChatMessageHistory:
    """给 RunnableWithMessageHistory 用: topic_id 就是 session_id"""
    if session_id not in _histories:
        _histories[session_id] = SQLiteChatMessageHistory(session_id)
    return _histories[session_id]
