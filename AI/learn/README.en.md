[简体中文](README.md) | [English](README.en.md)

# AI Chat Backend

Chat service built with Flask + LangChain + Zhipu GLM: guest/account dual-identity authentication, topic management, persistent chat history, streaming output, and RAG long-term memory based on vector retrieval.

## Features

- **Bundled identity model**: every device gets a guest credential and can start chatting right away; registration can "upgrade" the guest (id and history preserved), while login uses the account's own data — never merged
- **Single-token model**: each identity keeps only its latest token (valid for 7 days); re-login kicks the old device
- **Topic (session) management**: auto-created topics, manual creation, listing, per-topic history replay, deletion
- **Persistent memory**: every message is written to SQLite in real time — history survives restarts
- **RAG long-term memory**: each Q&A pair is embedded and stored; before each chat, the most relevant history is retrieved semantically and injected into the prompt
- **Semantic search API**: search your own chat history by meaning
- **Streaming output**: `/chat/stream` returns tokens as they are generated; the topic id is delivered via the `X-Topic-Id` response header

## Project Structure

```
learn/
├── app.py                  # Web layer: all Flask routes (auth / chat / topics / semantic search)
├── openapi.json            # API documentation (OpenAPI format)
├── data/
│   └── ai_chat.db          # SQLite database (auto-created at runtime; not committed to Git)
└── chatbot/                # Business package
    ├── config.py           # Config layer: models, prompts, Flask settings (only file to touch for config changes)
    ├── llm.py              # Model layer: creates the LLM instance; swap models here
    ├── prompts.py          # Prompt layer: all prompt templates in one place
    ├── chain.py            # Chain layer: model + prompt + memory assembled into the full chat chain
    ├── memory.py           # Memory layer: topic/message persistence + SQLite chat history
    ├── auth.py             # Auth layer: register / login / guest credentials / token management
    └── vector_store.py     # Vector layer: embed & store chat content + cosine similarity retrieval
```

## Requirements & Installation

- Python 3.10+ (the code uses `int | None` syntax)
- Dependencies: Flask, langchain, langchain-openai (current environment: Flask 3.1.3 / langchain 1.4.6 / langchain-openai 1.7.2)

```powershell
# from the repository root D:\word\AI
pip install flask langchain langchain-openai
```

## Configuration

All tunable parameters live in `chatbot/config.py`:

| Setting | Default | Description |
|---|---|---|
| `API_KEY` | required env var `Zhipu_GLM` | Zhipu Open Platform API key; never stored in source |
| `BASE_URL` | `https://open.bigmodel.cn/api/paas/v4/` | Zhipu API base URL |
| `MODEL_NAME` | `glm-5.3` | Chat model |
| `EMBED_MODEL` | `embedding-3` | Embedding model |
| `TEMPERATURE` | `0.6` | Sampling temperature |
| `SYSTEM_PROMPT` | helpful AI assistant persona | System prompt |
| `FLASK_HOST` / `FLASK_PORT` | `127.0.0.1` / `5000` | Server host and port |
| `FLASK_DEBUG` | `True` | Debug mode |

> 🔐 Security note: `config.py` does not store the API key. Set the environment variable before running:
>
> ```powershell
> $env:Zhipu_GLM = "your Zhipu API key"
> ```

## Running

```powershell
# from the repository root
.\.venv\Scripts\python.exe learn\app.py
```
> 📄 **Database preparation**: Git does not track `learn/data/*.db`. On first startup, or on first import of `chatbot.memory`, the app automatically creates `learn/data/ai_chat.db` and all tables. To initialize it early:
>
> ```powershell
> Push-Location learn
> ..\.venv\Scripts\python.exe -c "from chatbot.memory import init_db; init_db(); print('database ready')"
> Pop-Location
> ```
Once running, open `http://127.0.0.1:5000/` for service info; API docs are in `learn/openapi.json`.

## Authentication

All endpoints except `GET /` and `POST /auth/guest` require a credential. The primary credential is read from request headers in the following priority order (put the raw token value, no Bearer prefix needed):

```
Token: <token>          # recommended
X-Token: <token>
Authorization: Bearer <token>
```

For guest "upgrade" (and possible future merge flows): `X-Guest-Token: <guest token>`.

### Identity model

- Every guest/account is a separate row in the `users` table (`is_guest` flag); `user_id` auto-increments starting from 10000
- Registering with `X-Guest-Token` = guest upgrade: same id, history preserved seamlessly, phone & password filled in
- Login is just login: guest data stays with the guest identity; the account uses its own data
- Logout only revokes the official token; the frontend then fetches a fresh guest credential and returns to a "clean" guest state — old data remains on the server

## API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service info |
| POST | `/auth/guest` | Get a guest credential → `{token, expires_at, ...}` |
| POST | `/auth/register` | Register `{"phone", "password"}`; pass `X-Guest-Token` to upgrade a guest |
| POST | `/auth/login` | Login `{"phone", "password"}` |
| POST | `/auth/logout` | Revoke the current token |
| GET | `/auth/me` | Current identity (includes `is_guest`) |
| POST | `/chat` | One-shot chat `{"message", "topic_id"?}` |
| POST | `/chat/stream` | Streaming chat (topic id in the `X-Topic-Id` response header) |
| GET | `/topics` | Topic list for the current identity (with message counts) |
| POST | `/topics` | Create a topic `{"title"?}` |
| GET | `/topics/<id>/messages` | Full chat history of a topic |
| DELETE | `/topics/<id>` | Delete your own topic (messages cascade-deleted) |
| POST | `/memory/search` | Semantic search over your own history `{"query", "top_k"?}` |

### Example Calls

```powershell
# 1. Get a guest credential
$guest = Invoke-RestMethod -Method Post http://127.0.0.1:5000/auth/guest
$token = $guest.token

# 2. Chat (a topic is created automatically when topic_id is omitted)
Invoke-RestMethod -Method Post http://127.0.0.1:5000/chat `
  -Headers @{ Token = $token } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes('{"message":"Hello, introduce yourself"}'))

# 3. Streaming chat
Invoke-WebRequest -Method Post http://127.0.0.1:5000/chat/stream `
  -Headers @{ Token = $token } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes('{"message":"continue"}'))
```

## Database

SQLite file: `learn/data/ai_chat.db`. Git does not track `learn/data/*.db`; the first import of `chatbot.memory` creates the data directory, SQLite file, and all tables automatically. After cloning to a new environment, just start the app. To initialize early, run the command in the Running section.

| Table | Description |
|---|---|
| `users` | Identities: guests / registered users; `id` auto-increments from 10000 |
| `tokens` | Credentials: single token (unique index per identity), 7-day expiry |
| `topics` | Topics: `id` auto-increments from 1, owned by `user_id` |
| `messages` | Chat records: `topic_id` FK with cascade delete; `role` is `human` / `ai` |
| `context_vectors` | Vectors: chat content + vector stored as a JSON array |

## Memory & RAG Design

1. **Short-term memory**: `SQLiteChatMessageHistory` extends LangChain's in-memory history — each message is INSERTed in real time, cached in-process by `topic_id`
2. **Long-term memory (RAG)**: every Q&A pair is embedded with `embedding-3` and written to `context_vectors` (embedding failure never breaks the chat flow)
3. **Injection**: before each chat, the current message retrieves the top-3 similar records within the caller's own identity and appends them to the system prompt
4. **Retrieval**: currently SQLite-stored JSON vectors + in-memory cosine similarity; can be smoothly replaced with FAISS/Milvus later without changing the interface

## Known Caveats

- `app.py` keeps a temporary `AUTH-DEBUG` print block for `/auth/me`; remove it once header debugging is done
- Development mode `FLASK_DEBUG = True` — disable it in production and use a WSGI server (e.g. waitress/gunicorn) instead of the built-in one
- Semantic search loads all `context_vectors` and scores in memory; switch to a dedicated vector store as data grows
- To swap the chat model, only touch `chatbot/llm.py` (or `MODEL_NAME` in `config.py`)