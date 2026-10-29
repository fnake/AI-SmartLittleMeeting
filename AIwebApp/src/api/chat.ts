/** ===== 聊天：一次性回复 / 流式回复 ===== */
import type { ChatResult } from './types'
import { requestJson, requestStream } from '@/utils/request'

/** 一次性回复。topicId 不传则自动新建话题（标题取消息前 20 字） */
export function chatOnce(message: string, topicId?: number): Promise<ChatResult> {
  return requestJson<ChatResult>('/chat', {
    method: 'POST',
    body: topicId === undefined ? { message } : { message, topic_id: topicId },
  })
}

export interface ChatStreamOptions {
  /** 每收到一段增量文本时回调 */
  onDelta: (text: string) => void
  /** 中断生成 */
  signal?: AbortSignal
}

export interface ChatStreamResult {
  /** 完整回复文本 */
  reply: string
  /** 本次对话所属话题 ID（新建话题时从响应头 X-Topic-Id 获取，可能为 null） */
  topicId: number | null
}

/**
 * 流式回复：POST /chat/stream，响应为 text/plain 分段输出（底层走 utils/request 的 requestStream）。
 * 用法：
 *   const { reply, topicId } = await chatStream('你好', undefined, {
 *     onDelta: (t) => (aiMessage.content += t),
 *   })
 */
export async function chatStream(
  message: string,
  topicId: number | undefined,
  options: ChatStreamOptions,
): Promise<ChatStreamResult> {
  const { text, response } = await requestStream('/chat/stream', {
    body: topicId === undefined ? { message } : { message, topic_id: topicId },
    signal: options.signal,
    onDelta: options.onDelta,
  })

  // 新建话题时，话题 ID 通过响应头返回
  const headerTopicId = response.headers.get('X-Topic-Id')
  const topicIdResolved = headerTopicId !== null ? Number(headerTopicId) : null
  return { reply: text, topicId: topicIdResolved }
}
