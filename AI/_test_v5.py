# -*- coding: utf-8 -*-
"""v5 游客凭证模型离线测试: 独立临时库, 不碰真实 ai_chat.db, 不发网络请求"""
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent / "learn"))

import chatbot.memory as memory  # noqa: E402

TEST_DB = Path(tempfile.gettempdir()) / "ai_chat_v5_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
memory.DB_PATH = TEST_DB  # 必须在导入 auth/app 之前换库
memory.init_db()  # 在临时库上补建 topics/messages/context_vectors

import chatbot.auth as auth  # noqa: E402
from app import app  # noqa: E402

client = app.test_client()
results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {detail}"))

# 1 首页
r = client.get("/")
check("GET / 服务信息 5.0.0", r.status_code == 200 and r.get_json().get("version") == "5.0.0", r.data[:200])

# 2 无凭证访问受保护接口 -> 401
r = client.post("/chat", json={"message": "你好"})
check("无凭证 /chat -> 401 提示领游客凭证", r.status_code == 401 and "guest" in r.get_json()["error"], r.data[:200])
r = client.get("/topics")
check("无凭证 /topics -> 401", r.status_code == 401)

# 3 领游客凭证
r = client.post("/auth/guest")
j = r.get_json()
g1_token, g1_uid = j["token"], j["user_id"]
check("POST /auth/guest -> 201, 首个 user_id==10000", r.status_code == 201 and g1_uid == 10000, str(j))
H1 = {"Authorization": f"Bearer {g1_token}"}

# 4 游客建话题
r = client.post("/topics", headers=H1, json={"title": "游客一号的话题"})
t1 = r.get_json()
check("游客 POST /topics -> 201 归属自己", r.status_code == 201 and t1["user_id"] == g1_uid, r.data[:200])
client.post("/topics", headers=H1, json={"title": "游客一号的第二个话题"})

# 5 列表只看到自己的
r = client.get("/topics", headers=H1)
check("游客1 GET /topics -> 2 个", len(r.get_json()["topics"]) == 2, r.data[:300])

r = client.get("/topics", headers={"Token": g1_token})
check("Token 头鉴权等效(Authorization 兼容保留)", r.status_code == 200 and len(r.get_json()["topics"]) == 2)

# 6 游客2 隔离
j = client.post("/auth/guest").get_json()
g2_token, g2_uid = j["token"], j["user_id"]
H2 = {"Authorization": f"Bearer {g2_token}"}
client.post("/topics", headers=H2, json={"title": "游客二号的话题"})
r = client.get("/topics", headers=H2)
check("游客2 只看到自己 1 个话题(按凭证隔离)", len(r.get_json()["topics"]) == 1, r.data[:300])

# 7 越权删除 -> 404
r = client.delete(f"/topics/{t1['id']}", headers=H2)
check("游客2 删游客1话题 -> 404", r.status_code == 404)

# 8 /auth/me 游客
r = client.get("/auth/me", headers=H1)
j = r.get_json()
check("/auth/me 游客 is_guest=1", r.status_code == 200 and j["is_guest"] == 1, r.data[:200])

# 9 游客1转正: id 不变 + 数据保留
r = client.post("/auth/register", headers={**H1, "X-Guest-Token": g1_token},
                json={"phone": "13800000001", "password": "abc123"})
j = r.get_json()
check("游客1 带凭证注册转正: user_id 不变", r.status_code == 201 and j["user_id"] == g1_uid, r.data[:300])
r = client.get("/auth/me", headers=H1)
check("原token升级为正式用户", r.get_json()["is_guest"] == 0, r.data[:200])
r = client.get("/topics", headers=H1)
check("转正后话题仍在(无缝)", len(r.get_json()["topics"]) == 2, r.data[:300])

# 10 普通注册(无游客头) -> 只注册不登录
r = client.post("/auth/register", json={"phone": "13800000002", "password": "xyz789"})
check("普通注册 201 且无token", r.status_code == 201 and "token" not in r.get_json(), r.data[:200])

# 11 游客2 直接登录账号(无合并): 各自数据独立
r = client.post("/auth/login", json={"phone": "13800000001", "password": "abc123"})
j = r.get_json()
acc_token = j.get("token", "")
check("纯登录成功, 响应无 merged 字段", r.status_code == 200 and "merged" not in j, r.data[:300])
r = client.get("/topics", headers={"Token": acc_token})
check("账号只有自己2个话题(不带游客数据)", len(r.get_json()["topics"]) == 2, r.data[:300])
r = client.get("/topics", headers=H2)
check("游客2的数据仍归游客2", len(r.get_json()["topics"]) == 1, r.data[:300])
n = auth.query("SELECT COUNT(*) AS n FROM users WHERE id = ?", (g2_uid,), fetch=True)[0]["n"]
check("游客2身份仍存在", n == 1)

# 12 已转正的凭证不能再当游客头(退化为普通注册)
r = client.post("/auth/register", headers={"X-Guest-Token": g1_token},
                json={"phone": "13800000003", "password": "qwe456"})
check("转正后旧头失效 -> 普通注册", r.status_code == 201 and "token" not in r.get_json(), r.data[:200])

# 13 错误提示语
r = client.post("/auth/login", json={"phone": "13800000009", "password": "abc123"})
check("未注册手机号提示语", r.status_code == 400 and "未注册" in r.get_json()["error"], r.data[:200])
r = client.post("/auth/login", json={"phone": "13800000001", "password": "wrong!"})
check("密码错误提示语", r.status_code == 400 and "密码" in r.get_json()["error"], r.data[:200])
r = client.post("/auth/register", json={"phone": "13800000001", "password": "abc123"})
check("重复注册提示语", r.status_code == 400 and "已注册" in r.get_json()["error"], r.data[:200])

# 14 退出登录
r = client.post("/auth/logout", headers={"Authorization": f"Bearer {acc_token}"})
check("logout ok=true 提示语", r.get_json()["ok"] is True and "已注销" in r.get_json()["message"], r.data[:200])
r = client.get("/topics", headers={"Authorization": f"Bearer {acc_token}"})
check("退出后 /topics -> 401", r.status_code == 401)

# 15 单token模型: 重复登录顶掉旧token
j1 = client.post("/auth/login", json={"phone": "13800000001", "password": "abc123"}).get_json()
j2 = client.post("/auth/login", json={"phone": "13800000001", "password": "abc123"}).get_json()
check("两次登录 token 不同", j1["token"] != j2["token"])
r = client.get("/auth/me", headers={"Token": j1["token"]})
check("旧token已被顶掉 -> 401", r.status_code == 401, r.data[:200])
r = client.get("/auth/me", headers={"Token": j2["token"]})
check("最新token有效", r.status_code == 200, r.data[:200])
n = auth.query("SELECT COUNT(*) AS n FROM tokens WHERE user_id = ?",
               (j2["user_id"],), fetch=True)[0]["n"]
check("库中该身份只有1个token", n == 1)

# 汇总
fails = [x for x in results if not x[1]]
print(f"\n===== {len(results) - len(fails)}/{len(results)} passed =====")
if TEST_DB.exists():
    TEST_DB.unlink()
sys.exit(1 if fails else 0)