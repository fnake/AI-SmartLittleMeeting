/** ===== 话题管理 ===== */
import type { Message, Topic } from './types'
import { requestJson } from './http'

/** 话题列表（按创建时间倒序）。未登录/token 失效返回 401 */
export function listTopics(): Promise<{ topics: Topic[] }> {
  return requestJson<{ topics: Topic[] }>('/topics')
}

/** 新建话题。title 不传由服务端自动命名。返回 201 与话题对象 */
export function createTopic(title?: string): Promise<Topic> {
  return requestJson<Topic>('/topics', {
    method: 'POST',
    body: title === undefined ? {} : { title },
  })
}

/** 删除话题及其全部聊天记忆 */
export function deleteTopic(topicId: number): Promise<{ ok: true }> {
  return requestJson<{ ok: true }>(`/topics/${topicId}`, { method: 'DELETE' })
}

/** 话题的聊天记录：按时间正序全量返回。仅话题属主可见（401 未登录 / 404 不存在或不属于当前身份） */
export function listTopicMessages(
  topicId: number,
): Promise<{ topic: Topic; messages: Message[] }> {
  return requestJson<{ topic: Topic; messages: Message[] }>(`/topics/${topicId}/messages`)
}