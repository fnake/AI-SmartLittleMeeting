/** ===== 语义搜索历史记忆 / 话题聊天记录 ===== */
import type { MemorySearchResult } from './types'
import { requestJson } from './http'
import { listTopicMessages } from './topics'

/** 语义搜索当前身份自己的历史消息（余弦相似度倒序）。top_k 默认 5、最大 20 */
export function searchMemory(
  query: string,
  topK = 5,
  userId?: string,
): Promise<MemorySearchResult> {
  return requestJson<MemorySearchResult>('/memory/search', {
    method: 'POST',
    body: { query, top_k: topK, user_id: userId },
  })
}

export interface TopicHistoryMessage {
  role: 'user' | 'ai'
  content: string
  created_at?: string
}

/** 视为 AI 的角色值（兼容 LangChain 的 assistant/model 等历史数据） */
const AI_ROLES = new Set(['ai', 'assistant', 'model'])

/** 拉取话题完整聊天记录（GET /topics/{topic_id}/messages），时间正序 */
export async function fetchTopicHistory(topicId: number): Promise<TopicHistoryMessage[]> {
  const res = await listTopicMessages(topicId)
  return res.messages.map((msg) => {
    const raw = String(msg.role ?? '')
      .trim()
      .toLowerCase()
    return {
      role: AI_ROLES.has(raw) ? ('ai' as const) : ('user' as const),
      content: msg.content,
      created_at: msg.created_at,
    }
  })
}
