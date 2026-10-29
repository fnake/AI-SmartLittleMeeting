"""向量层 —— 把聊天内容变成向量存库, 支持按语义搜索历史

作用:
    - 每条聊天记录(用户问/AI答)都会生成一个向量(一串数字, 代表语义)
    - 语义相近的文字, 向量距离就近 -> 可以"按意思"搜历史
    - 用户登录后传 user_id 即可只搜自己的记忆 (topics.user_id 过滤)

原理: SQLite 当向量库(向量存成 JSON 文本), 搜索时内存算余弦相似度
以后数据量大再换 FAISS/Milvus 等专业向量库, 接口不用变
"""
import json
import math
from datetime import datetime

from langchain_openai import OpenAIEmbeddings

from chatbot.config import API_KEY, BASE_URL, EMBED_MODEL
from chatbot.memory import query

# 向量模型客户端(和聊天模型同一个智谱账号)
_embeddings = OpenAIEmbeddings(
    model=EMBED_MODEL,
    api_key=API_KEY,
    base_url=BASE_URL,
)


def embed(text: str) -> list[float]:
    """把一段文字变成向量(一串浮点数)"""
    return list(_embeddings.embed_query(text))


def add_message_vector(topic_id: str, role: str, content: str) -> None:
    """把一条聊天记录向量化后存入 context_vectors 表"""
    vec = embed(content)
    query(
        "INSERT INTO context_vectors (topic_id, role, content, vector, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (topic_id, role, content, json.dumps(vec),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def _cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度: 越接近 1 越相似"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def search_context(query_text: str, top_k: int = 5, user_id: str | None = None) -> list[dict]:
    """按语义搜索历史聊天

    user_id: 传了就只在该用户的话题范围内搜(登录后的用法)
             不传就全局搜(开发调试用)
    """
    # 确定搜索范围: user_id -> 该用户所有 topic_id
    if user_id:
        topics = query("SELECT id FROM topics WHERE user_id = ?", (user_id,), fetch=True)
        allowed = {t["id"] for t in topics}
        if not allowed:
            return []

    qvec = embed(query_text)
    rows = query(
        "SELECT topic_id, role, content, vector, created_at FROM context_vectors",
        fetch=True,
    )

    scored = []
    for r in rows:
        if user_id and r["topic_id"] not in allowed:
            continue
        score = _cosine(qvec, json.loads(r["vector"]))
        scored.append({
            "topic_id": r["topic_id"],
            "role": r["role"],
            "content": r["content"],
            "created_at": r["created_at"],
            "score": round(score, 4),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
