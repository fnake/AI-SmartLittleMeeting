/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 后端 API 地址，默认 http://127.0.0.1:5000 */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  appInfo?: { name: string; desktop: boolean }
}
