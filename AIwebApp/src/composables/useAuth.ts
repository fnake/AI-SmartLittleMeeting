/** 全局认证状态与操作（模块级单例，所有组件共享同一份 userInfo） */
import { ref } from 'vue'
import {
  ApiRequestError,
  clearToken,
  createGuest,
  getMe,
  getToken,
  login,
  logout,
  register,
} from '@/api'
import type { UserInfo } from '@/api'

const userInfo = ref<UserInfo | null>(null)

export function useAuth() {
  /** 拉取当前用户信息；token 失效时静默清理 */
  async function refreshMe(): Promise<void> {
    if (getToken() === null) {
      userInfo.value = null
      return
    }
    try {
      userInfo.value = await getMe()
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        clearToken()
        userInfo.value = null
        return
      }
      throw error
    }
  }

  /** 游客登录：领取游客凭证并自动保存 */
  async function loginAsGuest(): Promise<void> {
    await createGuest()
    await refreshMe()
  }

  /** 手机号 + 密码登录 */
  async function loginByPassword(phone: string, password: string): Promise<void> {
    await login(phone, password)
    await refreshMe()
  }

  /**
   * 注册。withGuestToken=true 时携带当前游客 token（游客转正，历史数据保留，注册即登录）；
   * false 为普通注册（注册后需手动登录）
   */
  async function registerAccount(
    phone: string,
    password: string,
    withGuestToken: boolean,
  ): Promise<UserInfo> {
    const guestToken = getToken()
    const res = await register(
      phone,
      password,
      withGuestToken && guestToken !== null ? { guestToken } : {},
    )
    if (!withGuestToken) clearToken()
    await refreshMe().catch(() => undefined)
    return res
  }

  /** 注销：调接口 + 清本地凭证 */
  async function signOut(): Promise<void> {
    try {
      await logout()
    } catch {
      // token 已失效也无妨，本地清理即可
    }
    clearToken()
    userInfo.value = null
  }

  return { userInfo, refreshMe, loginAsGuest, loginByPassword, registerAccount, signOut }
}
