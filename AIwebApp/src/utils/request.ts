/** ===== 统一请求层：BaseURL / Token 存储 / JSON 请求 / 流式请求 ===== */

export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:5000'
const TOKEN_KEY = 'ai_chat_token'

/* ---------- Token 存储 ---------- */

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/* ---------- 请求头 ---------- */

/** 组装请求头：Token 头（直接放值，非 Bearer） */
export function buildHeaders(extra?: Record<string, string>): Headers {
  const headers = new Headers(extra)
  const token = getToken()
  if (token !== null) headers.set('Token', token)
  return headers
}

/* ---------- 错误 ---------- */

/** 请求失败异常：携带状态码与后端 error 描述 */
export class ApiRequestError extends Error {
  readonly status: number
  readonly topicId?: number

  constructor(status: number, message: string, topicId?: number, cause?: unknown) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.topicId = topicId
    if (cause !== undefined) this.cause = cause
  }
}

interface ErrorBody {
  error?: string
  topic_id?: number
}

export async function parseErrorBody(res: Response): Promise<{ error: string; topic_id?: number }> {
  try {
    const data = (await res.json()) as ErrorBody
    return {
      error: data.error ?? `请求失败（HTTP ${res.status}）`,
      topic_id: data.topic_id,
    }
  } catch {
    return { error: `请求失败（HTTP ${res.status}）` }
  }
}

/* ---------- JSON 请求 ---------- */

interface JsonRequestOptions {
  method?: 'GET' | 'POST' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}

/** JSON 请求：成功返回解析后的 data，失败抛 ApiRequestError */
export async function requestJson<T>(path: string, options: JsonRequestOptions = {}): Promise<T> {
  const headers = buildHeaders(options.headers)
  const hasBody = options.body !== undefined
  if (hasBody) headers.set('Content-Type', 'application/json')

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: hasBody ? JSON.stringify(options.body) : undefined,
    })
  } catch (cause) {
    throw new ApiRequestError(0, `无法连接服务器（${BASE_URL}）`, undefined, cause)
  }

  if (!res.ok) {
    const { error, topic_id } = await parseErrorBody(res)
    throw new ApiRequestError(res.status, error, topic_id)
  }
  return (await res.json()) as T
}

/* ---------- 流式请求 ---------- */

export interface StreamRequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  /** 中断请求（AbortController.signal） */
  signal?: AbortSignal
  /** 每收到一段增量文本时回调 */
  onDelta: (text: string) => void
}

export interface StreamResult {
  /** 完整文本 */
  text: string
  /** 原始 Response（可读取响应头，如 X-Topic-Id） */
  response: Response
}

/**
 * 流式请求：fetch + ReadableStream 逐段解码 UTF-8 并回调增量文本。
 * 适用于 text/plain 分段输出（如 POST /chat/stream）。
 */
export async function requestStream(
  path: string,
  options: StreamRequestOptions,
): Promise<StreamResult> {
  const headers = buildHeaders()
  const hasBody = options.body !== undefined
  if (hasBody) headers.set('Content-Type', 'application/json')

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: options.method ?? 'POST',
      headers,
      signal: options.signal,
      body: hasBody ? JSON.stringify(options.body) : undefined,
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new ApiRequestError(0, `无法连接服务器（${BASE_URL}）`, undefined, cause)
  }

  if (!res.ok || res.body === null) {
    const { error, topic_id } = await parseErrorBody(res)
    throw new ApiRequestError(res.status, error, topic_id)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let text = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      if (chunk !== '') {
        text += chunk
        options.onDelta(chunk)
      }
    }
    // 冲刷解码器残余字节
    const tail = decoder.decode()
    if (tail !== '') {
      text += tail
      options.onDelta(tail)
    }
  } finally {
    reader.releaseLock()
  }

  return { text, response: res }
}
