# -*- coding: utf-8 -*-
"""在真实库上诊断 register 报错: 表结构 / 写锁探测 / 直接复现"""
import sqlite3, sys, traceback
sys.stdout.reconfigure(encoding="utf-8")
DB = r"D:\word\AI\learn\data\ai_chat.db"

print("=== 1. users 表结构 ===")
conn = sqlite3.connect(DB, timeout=2)
conn.row_factory = sqlite3.Row
for r in conn.execute("PRAGMA table_info(users)"):
    print(dict(r))
print("--- 索引 ---")
for i in conn.execute("PRAGMA index_list(users)").fetchall():
    cols = [c["name"] for c in conn.execute(f"PRAGMA index_info({i['name']})")]
    print(i["name"], "unique=", i["unique"], "cols=", cols)
conn.close()

print("\n=== 2. 写锁探测 ===")
try:
    c2 = sqlite3.connect(DB, timeout=2)
    c2.execute("BEGIN IMMEDIATE")
    c2.execute("ROLLBACK")
    c2.close()
    print("可写: 当前没有进程长期持锁")
except sqlite3.OperationalError as e:
    print("被锁住:", e)

print("\n=== 3. register 复现(新手机号, 成功则立即清理) ===")
sys.path.insert(0, r"D:\word\AI\learn")
from chatbot.auth import register, AuthError
phone = "19111112222"
try:
    r = register(phone, "test123456")
    print("register 成功:", r)
    import chatbot.memory as m
    m.query("DELETE FROM tokens WHERE user_id = ?", (r["user_id"],))
    m.query("DELETE FROM users WHERE id = ?", (r["user_id"],))
    print("(测试行已清理, 库恢复原样)")
except AuthError as e:
    print("AuthError(业务提示):", e)
except Exception:
    traceback.print_exc()