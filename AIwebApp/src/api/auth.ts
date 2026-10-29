/** ===== 认证：游客 / 注册 / 登录 / 注销 / 当前用户 ===== */
import type { LoginResponse, UserInfo } from './types'
import { requestJson, setToken } from './http'

/** 领取游客凭证（每台设备一个独立身份）。自动保存返回的 token */
export async function createGuest(): Promise<LoginResponse> {
  const res = await requestJson<LoginResponse>('/auth/guest', { method: 'POST' })
  setToken(res.token)
  return res
}

/**
 * 注册（手机号 + 密码）。
 * 传入 guestToken（当前游客 token）时游客「转正」：user_id 不变、历史数据保留。
 * 普通注册返回 {message: '注册成功，请登录'}；转正注册无需重新登录。
 */
export async function register(
  phone: string,
  password: string,
  options: { guestToken?: string } = {},
): Promise<UserInfo> {
  const headers: Record<string, string> = {}
  if (options.guestToken) headers['X-Guest-Token'] = options.guestToken
  return requestJson<UserInfo>('/auth/register', {
    method: 'POST',
    body: { phone, password },
    headers,
  })
}

/** 登录。注意：单 token 模型，重新登录会使该账号旧 token 全部失效。自动保存 token */
export async function login(phone: string, password: string): Promise<LoginResponse> {
  const res = await requestJson<LoginResponse>('/auth/login', {
    method: 'POST',
    body: { phone, password },
  })
  setToken(res.token)
  return res
}

/** 注销当前 token */
export function logout(): Promise<{ ok: true }> {
  return requestJson<{ ok: true }>('/auth/logout', { method: 'POST' })
}

/** 当前用户信息（游客或正式用户） */
export function getMe(): Promise<UserInfo> {
  return requestJson<UserInfo>('/auth/me')
}
