<div align="center">

# 小会 · AIwebApp

**AI Chat App — Web & Desktop**

[简体中文](#简体中文) | [English](#english)

</div>

---

<div align="center" id="简体中文">

## 简体中文

</div>

「小会」是一个 AI 对话应用前端，同时支持 **浏览器 Web 端** 与 **Electron 桌面端** 运行。基于 Vue 3 + TypeScript + Vite + Element Plus 构建，支持流式对话、多话题管理、游客/正式账号登录与历史记忆检索。

## ✨ 功能特性

- 💬 **流式对话**：`fetch + ReadableStream` 逐段渲染 AI 回复，支持随时中断生成
- 🗂 **多话题管理**：新建 / 切换 / 删除话题，话题标题自动生成，聊天记录按话题持久化
- 👤 **账号体系**：游客一键领取凭证、手机号注册/登录，游客可无损「转正」保留历史数据
- 🧠 **记忆检索**：支持对当前身份历史消息进行语义搜索（余弦相似度）
- 🖥 **桌面端**：Electron 打包，隐藏标题栏 + 自定义系统按钮样式
- 🇨🇳 **中文界面**：Element Plus 全局配置 zh-cn 语言包

## 🛠 技术栈

| 类别 | 技术 |
| --- | --- |
| 框架 | Vue 3.5（`<script setup>` 组合式 API） |
| 语言 | TypeScript 6 |
| 构建 | Vite 8 + vue-tsc |
| UI 组件 | Element Plus 2 + @element-plus/icons-vue |
| 路由 | Vue Router 4（hash 模式，兼容 Electron `file://` 加载） |
| 桌面端 | Electron 45 |
| 包管理 | pnpm |

## 📋 环境要求

- Node.js `^22.18.0 || >=24.12.0`
- pnpm（推荐）：`npm i -g pnpm`
- 后端服务：默认连接 `http://127.0.0.1:5000`，开发前请先启动后端（见下方[接口配置](#接口配置)）

## 🚀 快速开始

```bash
# 克隆项目
git clone https://github.com/your-username/AIwebApp.git
cd AIwebApp

# 安装依赖
pnpm install

# 仅启动 Web 端（浏览器访问 http://localhost:5173）
pnpm dev

# 启动桌面端（自动拉起 Vite dev server，端口就绪后打开 Electron 窗口）
pnpm desktop
```

## 📜 常用脚本

| 命令 | 说明 |
| --- | --- |
| `pnpm dev` | 启动 Vite 开发服务器（端口 5173，strictPort） |
| `pnpm desktop` | 开发模式启动 Electron 桌面端 |
| `pnpm app:start` | 以生产模式运行 Electron（加载 `dist/`，需先 build） |
| `pnpm build` | 类型检查 + 生产构建（输出到 `dist/`） |
| `pnpm build-only` | 仅构建，不做类型检查 |
| `pnpm type-check` | 仅运行 `vue-tsc` 类型检查 |
| `pnpm preview` | 本地预览生产构建产物 |

## 🔌 接口配置

统一请求层位于 `src/utils/request.ts`，通过环境变量 `VITE_API_BASE_URL` 配置后端地址，未配置时默认为：

```
http://127.0.0.1:5000
```

可在项目根目录创建 `.env.local` 文件自定义：

```env
VITE_API_BASE_URL=http://your-backend-host:port
```

认证采用单 token 模型：token 保存在 `localStorage`（键名 `ai_chat_token`），请求时通过 `Token` 请求头携带（非 Bearer）。收到 401 时自动清除本地 token 并弹出登录框。

## 📁 目录结构

```
├── electron/                # Electron 主进程与 preload 脚本
│   ├── main.mjs             # 主进程：创建窗口、加载 dev server 或 dist
│   └── preload.cjs
├── scripts/
│   ├── dev-desktop.mjs      # 桌面端开发启动器（Vite + Electron 联动）
│   └── test-*.mjs           # 后端接口联调测试脚本
├── src/
│   ├── api/                 # 接口层（按业务域拆分）
│   │   ├── http.ts          # 兼容层，统一从 utils/request 导出
│   │   ├── auth.ts          # 游客 / 注册 / 登录 / 注销 / 当前用户
│   │   ├── chat.ts          # 一次性回复 / 流式回复
│   │   ├── topics.ts        # 话题增删查、话题聊天记录
│   │   ├── memory.ts        # 语义记忆搜索
│   │   └── types.ts         # 接口类型定义
│   ├── components/          # 登录弹窗、登录表单
│   ├── composables/         # useAuth 等组合式函数
│   ├── router/              # 路由（hash 模式，全站单页：聊天主页）
│   ├── styles/              # 聊天界面样式
│   ├── utils/               # request.ts：BaseURL / Token / JSON / 流式请求
│   ├── views/               # 页面（index.vue：聊天主界面）
│   ├── App.vue
│   └── main.ts              # 入口：注册路由、Element Plus（zh-cn）
├── index.html
├── vite.config.ts
└── package.json
```

## 🏗 架构说明

- **路由**：使用 `createWebHashHistory`。Electron 生产模式通过 `file://` 加载 `dist/index.html`，hash 路由可避免路径问题；Vite `base` 同理配置为 `./` 相对路径。
- **请求层**：`utils/request.ts` 提供 `requestJson`（JSON 请求）与 `requestStream`（流式请求）两个基础方法；流式请求基于 `ReadableStream` 逐段解码 UTF-8 并回调增量文本，新建话题时从响应头 `X-Topic-Id` 取回话题 ID。
- **桌面端开发**：`scripts/dev-desktop.mjs` 不依赖 concurrently/wait-on，先启动 Vite，轮询端口就绪后再拉起 Electron，Electron 退出时自动关闭 Vite。

## 💡 推荐开发环境

- [VS Code](https://code.visualstudio.com/) + [Vue (Official) 扩展（Volar）](https://marketplace.visualstudio.com/items?itemName=Vue.volar)，请禁用 Vetur 以避免冲突。
- 调试建议安装 [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)。

---

<div align="center" id="english">

## English

</div>

**XiaoHui (AIwebApp)** is the frontend of an AI chat application that runs both in the **browser (Web)** and as an **Electron desktop app**. Built with Vue 3 + TypeScript + Vite + Element Plus, it supports streaming chat, multi-topic management, guest/registered accounts, and semantic memory search.

## ✨ Features

- 💬 **Streaming chat**: renders AI replies incrementally via `fetch + ReadableStream`, with the ability to abort generation at any time
- 🗂 **Multi-topic management**: create / switch / delete topics; titles are auto-generated and chat history is persisted per topic
- 👤 **Accounts**: one-click guest credentials, phone-number registration/login, and lossless guest-to-registered upgrade that keeps all history
- 🧠 **Memory search**: semantic search over your own chat history (cosine similarity ranking)
- 🖥 **Desktop**: Electron packaging with a hidden title bar and custom window-controls styling
- 🇨🇳 **Chinese UI**: Element Plus globally configured with the `zh-cn` locale

## 🛠 Tech Stack

| Category | Technology |
| --- | --- |
| Framework | Vue 3.5 (`<script setup>` Composition API) |
| Language | TypeScript 6 |
| Build | Vite 8 + vue-tsc |
| UI | Element Plus 2 + @element-plus/icons-vue |
| Routing | Vue Router 4 (hash mode, compatible with Electron `file://` loading) |
| Desktop | Electron 45 |
| Package manager | pnpm |

## 📋 Prerequisites

- Node.js `^22.18.0 || >=24.12.0`
- pnpm (recommended): `npm i -g pnpm`
- A backend service: the frontend connects to `http://127.0.0.1:5000` by default — start the backend before developing (see [API Configuration](#-api-configuration))

## 🚀 Getting Started

```bash
# Clone the project
git clone https://github.com/your-username/AIwebApp.git
cd AIwebApp

# Install dependencies
pnpm install

# Web only (open http://localhost:5173 in a browser)
pnpm dev

# Desktop (starts the Vite dev server, then launches the Electron window once the port is ready)
pnpm desktop
```

## 📜 Scripts

| Command | Description |
| --- | --- |
| `pnpm dev` | Start the Vite dev server (port 5173, strictPort) |
| `pnpm desktop` | Start the Electron desktop app in development mode |
| `pnpm app:start` | Run Electron in production mode (loads `dist/`; build first) |
| `pnpm build` | Type-check + production build (outputs to `dist/`) |
| `pnpm build-only` | Build without type-checking |
| `pnpm type-check` | Run `vue-tsc` type-checking only |
| `pnpm preview` | Preview the production build locally |

## 🔌 API Configuration

The unified request layer lives in `src/utils/request.ts`. The backend base URL is set via the `VITE_API_BASE_URL` environment variable and defaults to:

```
http://127.0.0.1:5000
```

Create a `.env.local` file in the project root to customize it:

```env
VITE_API_BASE_URL=http://your-backend-host:port
```

Authentication uses a single-token model: the token is stored in `localStorage` (key `ai_chat_token`) and sent via the `Token` request header (not `Bearer`). On a 401 response the client clears the local token and opens the login dialog automatically.

## 📁 Project Structure

```
├── electron/                # Electron main process and preload script
│   ├── main.mjs             # Main process: creates the window, loads dev server or dist
│   └── preload.cjs
├── scripts/
│   ├── dev-desktop.mjs      # Desktop dev launcher (Vite + Electron orchestration)
│   └── test-*.mjs           # Backend API integration test scripts
├── src/
│   ├── api/                 # API layer (split by domain)
│   │   ├── http.ts          # Compatibility layer re-exporting utils/request
│   │   ├── auth.ts          # Guest / register / login / logout / current user
│   │   ├── chat.ts          # One-shot reply / streaming reply
│   │   ├── topics.ts        # Topic CRUD and per-topic chat history
│   │   ├── memory.ts        # Semantic memory search
│   │   └── types.ts         # API type definitions
│   ├── components/          # Login dialog, login form
│   ├── composables/         # useAuth and other composables
│   ├── router/              # Router (hash mode; single page: chat home)
│   ├── styles/              # Chat UI styles
│   ├── utils/               # request.ts: base URL / token / JSON / streaming requests
│   ├── views/               # Pages (index.vue: main chat view)
│   ├── App.vue
│   └── main.ts              # Entry: registers router, Element Plus (zh-cn)
├── index.html
├── vite.config.ts
└── package.json
```

## 🏗 Architecture Notes

- **Routing**: uses `createWebHashHistory`. In production Electron loads `dist/index.html` via `file://`, so hash routing avoids path issues; Vite's `base` is likewise set to the relative `./`.
- **Request layer**: `utils/request.ts` provides two primitives — `requestJson` (JSON requests) and `requestStream` (streaming requests). Streaming decodes UTF-8 chunk by chunk from a `ReadableStream` and invokes a callback per delta; when a new topic is created, its ID is read from the `X-Topic-Id` response header.
- **Desktop development**: `scripts/dev-desktop.mjs` avoids concurrently/wait-on — it starts Vite first, polls until the port is ready, then launches Electron; quitting Electron automatically shuts Vite down.

## 💡 Recommended Dev Environment

- [VS Code](https://code.visualstudio.com/) + [Vue (Official) extension (Volar)](https://marketplace.visualstudio.com/items?itemName=Vue.volar); disable Vetur to avoid conflicts.
- For debugging, install [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd).

---

<div align="center">

Made with ❤️ · 小会 AIwebApp

</div>
