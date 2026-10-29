[简体中文](README.md) | [English](README.en.md)

# AI Chat 后端

Flask + LangChain + 智谱 GLM 的聊天服务：游客/账号双身份认证、话题管理、持久化聊天历史、流式输出、基于向量检索的长期记忆（RAG）。

## 功能特性

- **豆包式身份模型**：每台设备先领一个游客凭证即可开聊；注册可"转正"（id 和历史数据不变），登录使用账号自己的数据，互不合并
- **单 Token 模型**：同一身份只保留最新一个 token（有效期 7 天），重新登录会顶掉旧设备
- **话题（会话）管理**：自动建题、手动建题、列表、按题回放历史、删除
- **持久化记忆**：聊天记录实时写入 SQLite，重启后历史不丢
- **RAG 长期记忆**：每问每答向量化入库，聊天前按语义检索最相关的历史注入 prompt
- **语义搜索接口**：按语义搜索当前身份自己的历史聊天
- **流式输出**：`/chat/stream` 边生成边返回，话题 ID 通过响应头 `X-Topic-Id` 下发

## 项目结构

```
learn/
├── app.py                  # Web 层：所有 Flask 路由（认证 / 聊天 / 话题 / 语义搜索）
├── openapi.json            # 接口文档（OpenAPI 格式）
├── data/
│   └── ai_chat.db          # SQLite 数据库（当前使用）
└── chatbot/                # 业务包
    ├── config.py           # 配置层：模型、提示词、Flask 参数（改配置只动这里）
    ├── llm.py              # 模型层：创建 LLM 实例，换模型只改这里
    ├── prompts.py          # 提示词层：prompt 模板集中管理
    ├── chain.py            # 链层：模型 + 提示词 + 记忆 组装成完整聊天链
    ├── memory.py           # 记忆层：话题/消息持久化 + SQLite 聊天历史
    ├── auth.py             # 认证层：注册 / 登录 / 游客凭证 / token 管理
    └── vector_store.py     # 向量层：聊天内容向量化入库 + 余弦相似度检索
```

## 环境要求与安装

- Python 3.10+（代码使用了 `int | None` 语法）
- 依赖：Flask、langchain、langchain-openai（当前环境版本：Flask 3.1.3 / langchain 1.4.6 / langchain-openai 1.7.2）

```powershell
# 在仓库根目录 D:\word\AI 下
pip install flask langchain langchain-openai
```

## 配置

所有可调参数集中在 `chatbot/config.py`：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `API_KEY` | 必须通过环境变量 `Zhipu_GLM` 提供 | 智谱开放平台 API Key，不写入代码 |
| `BASE_URL` | `https://open.bigmodel.cn/api/paas/v4/` | 智谱 API 地址 |
| `MODEL_NAME` | `glm-5.3` | 聊天模型 |
| `EMBED_MODEL` | `embedding-3` | 向量模型 |
| `TEMPERATURE` | `0.6` | 采样温度 |
| `SYSTEM_PROMPT` | AI 小助手人设 | 系统提示词 |
| `FLASK_HOST` / `FLASK_PORT` | `127.0.0.1` / `5000` | 服务地址端口 |
| `FLASK_DEBUG` | `True` | 调试模式 |

> 🔐 安全提示：`config.py` 不保存 API Key。运行前请设置环境变量：
>
> ```powershell
> $env:Zhipu_GLM = "你的智谱 API Key"
> ```

## 启动

```powershell
# 仓库根目录下
.\.venv\Scripts\python.exe learn\app.py
```

启动后访问 `http://127.0.0.1:5000/` 可看到服务信息，接口文档见 `learn/openapi.json`。

## 认证方式

除 `GET /` 和 `POST /auth/guest` 外，所有接口都需要凭证。请求头按以下优先级取主凭证（直接放 token 值，不用加 Bearer 前缀）：

```
Token: <token>          # 推荐
X-Token: <token>
Authorization: Bearer <token>
```

游客"转正"或后续扩展合并场景使用：`X-Guest-Token: <游客token>`。

### 身份模型说明

- 每个游客/账号都是 `users` 表里的一个独立身份（`is_guest` 标记），`user_id` 从 10000 起自增
- 注册时带 `X-Guest-Token` = 游客转正：id 不变、历史数据无缝保留，只补上手机号密码
- 登录就是登录：游客数据留在游客身份里，账号用账号自己的数据
- 退出登录只废止正式 token；前端重新领游客凭证后回到"清零"的游客态，旧数据仍在服务器

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务信息 |
| POST | `/auth/guest` | 领取游客凭证 → `{token, expires_at, ...}` |
| POST | `/auth/register` | 注册 `{"phone", "password"}`，可带 `X-Guest-Token` 转正 |
| POST | `/auth/login` | 登录 `{"phone", "password"}` |
| POST | `/auth/logout` | 注销当前 token |
| GET | `/auth/me` | 当前身份信息（含 `is_guest`） |
| POST | `/chat` | 一次性聊天 `{"message", "topic_id"?}` |
| POST | `/chat/stream` | 流式聊天（话题 ID 在响应头 `X-Topic-Id`） |
| GET | `/topics` | 当前身份的话题列表（含消息条数） |
| POST | `/topics` | 新建话题 `{"title"?}` |
| GET | `/topics/<id>/messages` | 某话题的完整聊天记录 |
| DELETE | `/topics/<id>` | 删除自己的话题（消息级联删除） |
| POST | `/memory/search` | 语义搜索自己的历史 `{"query", "top_k"?}` |

### 调用示例

```powershell
# 1. 领游客凭证
$guest = Invoke-RestMethod -Method Post http://127.0.0.1:5000/auth/guest
$token = $guest.token

# 2. 聊天（不传 topic_id 会自动建话题）
Invoke-RestMethod -Method Post http://127.0.0.1:5000/chat `
  -Headers @{ Token = $token } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes('{"message":"你好，介绍一下你自己"}'))

# 3. 流式聊天
Invoke-WebRequest -Method Post http://127.0.0.1:5000/chat/stream `
  -Headers @{ Token = $token } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes('{"message":"继续"}'))
```

## 数据库

SQLite 文件：`learn/data/ai_chat.db`，首次导入 `chatbot.memory` 时自动建表。

| 表 | 说明 |
|---|---|
| `users` | 身份表：游客/正式用户，`id` 从 10000 起自增 |
| `tokens` | 凭证表：单 token（每身份唯一索引），7 天过期 |
| `topics` | 话题表：`id` 从 1 起自增，归属 `user_id` |
| `messages` | 聊天记录表：`topic_id` 外键级联删除，`role` 为 `human` / `ai` |
| `context_vectors` | 向量表：聊天内容 + JSON 数组形式的向量 |

## 记忆与 RAG 原理

1. **短期记忆**：`SQLiteChatMessageHistory` 继承 LangChain 的内存历史，每条消息实时 INSERT 入库，进程内按 `topic_id` 缓存
2. **长期记忆（RAG）**：每问一答都调用 `embedding-3` 向量化后写入 `context_vectors`（向量化失败不影响聊天主流程）
3. **注入**：每次聊天前，用当前消息在本身份范围内检索 top-3 相似历史，拼进 system prompt
4. **检索**：目前是 SQLite 存 JSON 向量 + 内存余弦相似度；数据量大后可平滑换 FAISS/Milvus，接口不变

## 已知注意事项

- `app.py` 中保留了一段 `/auth/me` 的 `AUTH-DEBUG` 打印代码，排查完鉴权头后应删除
- 开发模式 `FLASK_DEBUG = True`，生产部署请关闭，并用 WSGI 服务器（如 waitress/gunicorn）替代内置服务器
- 语义搜索是全量载入 `context_vectors` 后内存打分，数据量大后建议换专业向量库
- 换聊天模型只改 `chatbot/llm.py`（或 `config.py` 的 `MODEL_NAME`）