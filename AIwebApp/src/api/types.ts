/** ===== 类型定义（依据 Apifox「AI Chat API (Flask + LangChain)」生成） ===== */

/** 用户信息：游客 is_guest=1，正式用户 is_guest=0 */
export interface UserInfo {
  user_id: number
  is_guest: 0 | 1
  phone: string | null
  identity?: string
  message?: string
}

/** 登录 / 领取游客凭证的返回 */
export interface LoginResponse {
  token: string
  user_id: number
  phone?: string | null
  /** token 过期时间，7 天有效 */
  expires_at: string
  message: string
}

/** 话题 */
export interface Topic {
  id: number
  title: string
  created_at: string
  /** 消息条数（含问答双方） */
  message_count: number
  user_id: number
}

/** /chat 一次性回复 */
export interface ChatResult {
  reply: string
  topic_id: number
}

/** /memory/search 命中项 */
export interface MemoryHit {
  topic_id: number
  role: 'human' | 'ai'
  content: string
  /** 余弦相似度 0~1 */
  score: number
  created_at?: string
}

export interface MemorySearchResult {
  results: MemoryHit[]
}

/** 统一错误结构 */
export interface ApiErrorBody {
  error: string
  topic_id?: number
}

/** 聊天消息（GET /topics/{topic_id}/messages 返回，时间正序） */
export interface Message {
  id: number
  role: 'human' | 'ai'
  content: string
  created_at: string
}