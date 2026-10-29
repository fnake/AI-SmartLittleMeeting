"""Web 层 —— Flask 纯 API: 游客凭证 + 手机号登录 + 话题管理 + 聊天(RAG记忆) + 语义搜索

运行:
    .\\.venv\\Scripts\\python.exe learn\\app.py

鉴权(豆包式身份, 每台设备一个独立身份):
    - POST /auth/guest 领游客凭证, 前端存本地, 之后每次请求都带上
    - 主凭证: 请求头 Token: <token>   (游客态和登录态格式相同, 直接放 token 值)
    - 每个凭证对应 users 表一个独立身份, 数据按凭证完全隔离
    - 注册时带 X-Guest-Token: 游客"转正"(id不变, 历史数据无缝保留)
    - 登录与游客数据无关: 游客就是游客, 登录后用的就是账号自己的数据
    - 退出登录后前端换一个新游客凭证 -> 界面"清零", 旧数据仍留在服务器

接口一览:
    GET    /                   服务信息
    POST   /auth/guest         领取游客凭证 -> token
    POST   /auth/register      注册  {"phone", "password"}, 可带头 X-Guest-Token 转正
    POST   /auth/login         登录  {"phone", "password"}, 可带头 X-Guest-Token 合并
    POST   /auth/logout        注销 token
    GET    /auth/me            当前身份信息(含 is_guest)
    POST   /chat               聊天(一次性)  {"message", "topic_id"?}
    POST   /chat/stream        聊天(流式)    话题ID在响应头 X-Topic-Id
    GET    /topics             当前身份的话题列表
    POST   /topics             新建话题
    GET    /topics/<id>/messages 某话题的聊天记录
    DELETE /topics/<id>        删除自己的话题
    POST   /memory/search      语义搜索自己的历史
"""
import traceback

from flask import Flask, Response, jsonify, request

from chatbot.auth import (
    AuthError,
    create_guest,
    login,
    logout,
    register,
    user_from_token,
)
from chatbot.chain import chat
from chatbot.config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT
from chatbot.memory import (
    create_topic,
    delete_topic,
    get_messages,
    get_topic,
    list_topics,
)
from chatbot.vector_store import add_message_vector, search_context

app = Flask(__name__)


# TODO 临时调试: 查看 /auth/me 实际收到的鉴权头, 排查完删除这个函数
@app.before_request
def _auth_debug():
    if request.path == "/auth/me":
        print("[AUTH-DEBUG] Token 头     :", repr(request.headers.get("Token")))
        print("[AUTH-DEBUG] X-Token 头   :", repr(request.headers.get("X-Token")))
        print("[AUTH-DEBUG] Authorization:", repr(request.headers.get("Authorization")))


# ---------- 鉴权辅助 ----------
def _bearer_token() -> str:
    """从请求头取主凭证, 优先级: Token > X-Token > Authorization: Bearer
    推荐前端统一用  Token: <token>  (直接放 token 值, 不用加 Bearer 前缀)
    """
    
    token = request.headers.get("Token", "").strip()
    token = token or request.headers.get("X-Token", "").strip()
    if not token:
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.startswith("Bearer ") else ""
    return token


def _guest_token() -> str:
    """从请求头取游客凭证: X-Guest-Token: <token>(注册转正/登录合并时用)"""
    return request.headers.get("X-Guest-Token", "").strip()


def current_user() -> dict | None:
    """解析主凭证 -> 身份 {user_id, phone, is_guest}; 无效返回 None"""
    return user_from_token(_bearer_token())


def current_uid() -> int | None:
    """当前身份ID; 没带有效凭证返回 None(前端应先 POST /auth/guest)"""
    user = current_user()
    return user["user_id"] if user else None


def uid_or_error() -> tuple[int | None, tuple | None]:
    """受保护接口统一入口校验: 返回 (身份ID, 错误响应), 二者必有一个为 None"""
    uid = current_uid()
    if uid is None:
        return None, (jsonify({"error": "请先登录或获取游客身份(POST /auth/guest)"}), 401)
    return uid, None


def guest_uid_from_header() -> int | None:
    """X-Guest-Token -> 游客身份ID; 无效或不是游客返回 None"""
    user = user_from_token(_guest_token())
    return user["user_id"] if user and user["is_guest"] else None


def resolve_topic(data: dict, uid: int) -> tuple[dict | None, str | None]:
    """解析话题: 传 topic_id 校验存在且属于自己; 没传则自动新建"""
    raw = data.get("topic_id")
    if raw not in (None, ""):
        topic = get_topic(int(raw))
        if not topic or topic["user_id"] != uid:
            return None, "话题不存在"
        return topic, None
    message = str(data.get("message", "")).strip()
    return create_topic(title=message[:20] or None, user_id=uid), None


def build_memory_block(message: str, uid: int) -> str:
    """RAG: 检索当前身份的相关历史记忆, 拼成注入 prompt 的文字块(游客/用户各自隔离)"""
    try:
        memories = search_context(message, top_k=3, user_id=uid)
        return "\n".join(
            f"- [{m['created_at']}] {m['role']}: {m['content']}" for m in memories
        ) or "（无相关历史记忆）"
    except Exception:
        traceback.print_exc()
        return "（无相关历史记忆）"


def save_memory_vectors(topic_id: int, message: str, reply: str) -> None:
    """把一问一答向量化入库(失败不影响聊天主流程)"""
    try:
        add_message_vector(topic_id, "human", message)
        add_message_vector(topic_id, "ai", reply)
    except Exception:
        traceback.print_exc()


# ---------- 认证接口 ----------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"name": "AI Chat API", "version": "5.0.0", "docs": "openapi.json"})


@app.route("/auth/guest", methods=["POST"])
def auth_guest():
    """发一个游客身份: 前端保存返回的 token, 之后所有请求带上它"""
    return jsonify(create_guest()), 201


@app.route("/auth/register", methods=["POST"])
def auth_register():
    """注册; 带 X-Guest-Token = 游客转正(id和数据不变, 补上手机号密码)"""
    data = request.get_json(silent=True) or {}
    try:
        result = register(data.get("phone"), data.get("password"),
                          upgrade_user_id=guest_uid_from_header())
        return jsonify(result), 201
    except AuthError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/auth/login", methods=["POST"])
def auth_login():
    """登录: 纯手机号+密码校验, 与游客数据无关"""
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(login(data.get("phone"), data.get("password")))
    except AuthError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    ok = logout(_bearer_token())
    msg = "已注销" if ok else "token 无效或已失效"
    return jsonify({"ok": ok, "message": msg})


@app.route("/auth/me", methods=["GET"])
def auth_me():
    user = current_user()
    if not user:
        return jsonify({"error": "token 无效或已过期"}), 401
    return jsonify({**user, "identity": "游客" if user["is_guest"] else "正式用户"})


# ---------- 聊天接口 ----------
@app.route("/chat", methods=["POST"])
def chat_once():
    uid, err = uid_or_error()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    topic, terr = resolve_topic(data, uid)
    if terr:
        return jsonify({"error": terr}), 404

    cfg = {"configurable": {"session_id": topic["id"]}}
    memory_block = build_memory_block(message, uid)
    try:
        result = chat.invoke({"input": message, "memory": memory_block}, cfg)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"模型调用失败: {type(e).__name__}: {e}", "topic_id": topic["id"]}), 502

    save_memory_vectors(topic["id"], message, result.content)
    return jsonify({"reply": result.content, "topic_id": topic["id"]})


@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    uid, err = uid_or_error()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "消息不能为空"}), 400

    topic, terr = resolve_topic(data, uid)
    if terr:
        return jsonify({"error": terr}), 404

    cfg = {"configurable": {"session_id": topic["id"]}}
    memory_block = build_memory_block(message, uid)

    def generate():
        collected = []
        try:
            for chunk in chat.stream({"input": message, "memory": memory_block}, cfg):
                if chunk.content:
                    collected.append(chunk.content)
                    yield chunk.content
        except Exception as e:
            traceback.print_exc()
            yield f"\n[模型调用失败: {type(e).__name__}: {e}]"
        if collected:
            save_memory_vectors(topic["id"], message, "".join(collected))

    return Response(generate(), mimetype="text/plain; charset=utf-8",
                    headers={"X-Topic-Id": topic["id"]})


# ---------- 话题接口 ----------
@app.route("/topics", methods=["GET"])
def topics_list():
    """当前身份的话题列表(游客=本机这个游客的; 用户=自己的)"""
    uid, err = uid_or_error()
    if err:
        return err
    return jsonify({"topics": list_topics(uid)})


@app.route("/topics", methods=["POST"])
def topics_create():
    """手动新建话题(游客和用户都可以, 归属当前身份)"""
    uid, err = uid_or_error()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip() or None
    topic = create_topic(title, user_id=uid)
    return jsonify(topic), 201


@app.route("/topics/<int:topic_id>/messages", methods=["GET"])
def topics_messages(topic_id: int):
    """某话题的完整聊天记录(仅本人可见), 用于刷新/重启后回显历史消息"""
    uid, err = uid_or_error()
    if err:
        return err
    topic = get_topic(topic_id)
    if not topic or topic["user_id"] != uid:
        return jsonify({"error": "话题不存在"}), 404
    return jsonify({"topic": topic, "messages": get_messages(topic_id)})


@app.route("/topics/<int:topic_id>", methods=["DELETE"])
def topics_delete(topic_id: int):
    uid, err = uid_or_error()
    if err:
        return err
    topic = get_topic(topic_id)
    if not topic or topic["user_id"] != uid:
        return jsonify({"error": "话题不存在"}), 404
    delete_topic(topic_id)
    return jsonify({"ok": True})


# ---------- 语义搜索 ----------
@app.route("/memory/search", methods=["POST"])
def memory_search():
    """按语义搜索当前身份自己的历史聊天(游客搜游客的, 用户搜自己的)"""
    uid, err = uid_or_error()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    q = str(data.get("query", "")).strip()
    if not q:
        return jsonify({"error": "查询不能为空"}), 400
    top_k = min(int(data.get("top_k", 5)), 20)
    try:
        results = search_context(q, top_k=top_k, user_id=uid)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"检索失败: {type(e).__name__}: {e}"}), 502
    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
